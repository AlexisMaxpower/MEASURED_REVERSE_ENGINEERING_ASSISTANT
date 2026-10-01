from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.calibration import CalibrationService
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.guidance import GuidedCaptureAction, GuidedCaptureReadinessService
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureQualityMetrics,
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureSession,
    CaptureViewType,
    FrameKind,
    MeasurementMatProfile,
    PartContext,
    Project,
)
from mrea_capture.quality import CaptureQualityService
from mrea_capture.rectification import RectificationService, RectifiedRaster
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService, CaptureWorkflowError


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=640, height_px=480, device_model="FixtureCam")


def _profile() -> MeasurementMatProfile:
    return MeasurementMatProfile(
        mat_id="MAT-A4-V1",
        squares_x=5,
        squares_y=7,
        square_length_mm=20,
        marker_length_mm=14,
    )


class _Detector:
    def detect(self, image_bytes, *, profile, view, source_frame_id):
        return CalibrationResult(
            view=view,
            source_frame_id=source_frame_id,
            mat_id=profile.mat_id,
            homography=[1, 0, 0, 0, 1, 0, 0, 0, 1],
            detected_marker_count=12,
            detected_charuco_corner_count=24,
            reprojection_rmse_mm=0.1,
        )


class _Analyzer:
    def analyze(self, image_bytes, *, source_frame_id, view, calibration=None, mat_profile=None):
        return CaptureQualityResult(
            analysis_id=uuid5(NAMESPACE_URL, f"test:quality:{source_frame_id}"),
            source_frame_id=source_frame_id,
            view=view,
            calibration_id=calibration.calibration_id if calibration else None,
            mat_id=mat_profile.mat_id if mat_profile else calibration.mat_id if calibration else None,
            policy_version="test.quality.v1",
            verdict=CaptureQualityVerdict.ACCEPT,
            metrics=CaptureQualityMetrics(
                laplacian_variance=100,
                mean_luma=120,
                dark_clipped_fraction=0,
                bright_clipped_fraction=0,
                glare_proxy_fraction=0,
                edge_density=0.1,
                border_edge_ratio=0.1,
            ),
        )


class _Normalizer:
    def normalize(self, image_bytes, *, calibration, profile, pixels_per_mm):
        payload = f"rectified:{calibration.source_frame_id}".encode()
        return RectifiedRaster(payload, width_px=1000, height_px=1400)


def _fixture(tmp_path: Path):
    project = Project(name="Recapture fixture", part=PartContext(part_type="flat plate"))
    plan = CapturePlanService().create_plan(project)
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    calibration = CalibrationService(repo, store, _Detector())
    quality = CaptureQualityService(repo, store, _Analyzer())
    rectification = RectificationService(repo, store, _Normalizer())
    return project, repo, store, capture, calibration, quality, rectification, session


def test_recapture_preserves_history_and_switches_active_attempt(tmp_path: Path) -> None:
    (
        project,
        _,
        store,
        capture,
        calibration,
        quality,
        rectification,
        session,
    ) = _fixture(tmp_path)
    profile = _profile()

    clean_v1 = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-v1",
        camera=_camera(),
    )
    cal_v1 = calibration.calibrate_view(
        session.session_id, view=CaptureViewType.FRONT, profile=profile
    )
    quality_v1 = quality.analyze_clean_reference(
        session.session_id, view=CaptureViewType.FRONT, mat_profile=profile
    )
    measurement_v1 = capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement-v1",
        camera=_camera(),
    )
    rect_v1 = rectification.rectify_view(
        session.session_id, view=CaptureViewType.FRONT, profile=profile
    )

    clean_v2 = capture.recapture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-v2",
        camera=_camera(),
    )
    after_recapture = capture.get(session.session_id)
    progress = after_recapture.views[0]

    assert clean_v2.supersedes_frame_id == clean_v1.frame_id
    assert progress.active_clean_reference_frame_id == clean_v2.frame_id
    assert store.get_bytes(clean_v1.artifact) == b"clean-v1"
    assert store.get_bytes(clean_v2.artifact) == b"clean-v2"
    assert measurement_v1.source_clean_reference_frame_id == clean_v1.frame_id
    assert cal_v1.source_frame_id == clean_v1.frame_id
    assert quality_v1.source_frame_id == clean_v1.frame_id
    assert rect_v1.source_frame_id == clean_v1.frame_id

    readiness = GuidedCaptureReadinessService().evaluate(after_recapture)
    assert readiness.next_action is GuidedCaptureAction.RUN_CALIBRATION
    assert readiness.views[0].clean_reference_frame_id == clean_v2.frame_id
    assert readiness.views[0].measurement_frame_count == 0

    cal_v2 = calibration.calibrate_view(
        session.session_id, view=CaptureViewType.FRONT, profile=profile
    )
    quality_v2 = quality.analyze_clean_reference(
        session.session_id, view=CaptureViewType.FRONT, mat_profile=profile
    )
    measurement_v2 = capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement-v2",
        camera=_camera(),
    )
    rect_v2 = rectification.rectify_view(
        session.session_id, view=CaptureViewType.FRONT, profile=profile
    )

    restored = capture.get(session.session_id)
    assert len([f for f in restored.frames if f.kind is FrameKind.CLEAN_REFERENCE]) == 2
    assert len(restored.calibrations) == 2
    assert len(restored.quality_analyses) == 2
    assert len(restored.rectified_references) == 2
    assert measurement_v2.source_clean_reference_frame_id == clean_v2.frame_id
    assert cal_v2.source_frame_id == clean_v2.frame_id
    assert quality_v2.source_frame_id == clean_v2.frame_id
    assert rect_v2.source_frame_id == clean_v2.frame_id

    package = CanonicalContractBuilder.capture_package(project, restored)
    canonical_view = package["views"][0]
    assert canonical_view["clean_reference_frame"]["artifact_id"] == str(clean_v2.artifact.artifact_id)
    assert [item["frame_id"] for item in canonical_view["measurement_frames"]] == [
        str(measurement_v2.frame_id)
    ]
    assert canonical_view["calibration"]["mat_id"] == profile.mat_id


def test_recapture_after_quality_reject_is_an_executable_next_action(tmp_path: Path) -> None:
    project, repo, _, capture, calibration, _, _, session = _fixture(tmp_path)
    profile = _profile()
    clean = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-rejected",
        camera=_camera(),
    )
    calibration.calibrate_view(session.session_id, view=CaptureViewType.FRONT, profile=profile)

    stored = capture.get(session.session_id)
    from mrea_capture.models import CaptureQualityFinding, QualityReasonCode, QualitySeverity

    stored.quality_analyses.append(
        CaptureQualityResult(
            analysis_id=UUID("00000000-0000-0000-0000-000000000777"),
            source_frame_id=clean.frame_id,
            view=CaptureViewType.FRONT,
            calibration_id=stored.calibrations[0].calibration_id,
            mat_id=profile.mat_id,
            policy_version="test.reject.v1",
            verdict=CaptureQualityVerdict.REJECT,
            metrics=CaptureQualityMetrics(
                laplacian_variance=1,
                mean_luma=120,
                dark_clipped_fraction=0,
                bright_clipped_fraction=0,
                glare_proxy_fraction=0,
                edge_density=0.1,
                border_edge_ratio=0.1,
            ),
            findings=[
                CaptureQualityFinding(
                    code=QualityReasonCode.BLUR,
                    severity=QualitySeverity.REJECT,
                    metric="laplacian_variance",
                    observed=1,
                    threshold=20,
                    comparison="<",
                )
            ],
        )
    )
    repo.save(stored)

    before = GuidedCaptureReadinessService().evaluate(capture.get(session.session_id))
    assert before.next_action is GuidedCaptureAction.RECAPTURE_CLEAN_REFERENCE

    replacement = capture.recapture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"replacement",
        camera=_camera(),
    )
    after = GuidedCaptureReadinessService().evaluate(capture.get(session.session_id))
    assert replacement.supersedes_frame_id == clean.frame_id
    assert after.next_action is GuidedCaptureAction.RUN_CALIBRATION
    assert after.views[0].quality_analysis_id is None


def test_legacy_single_clean_session_backfills_lineage(tmp_path: Path) -> None:
    _, _, _, capture, _, _, _, session = _fixture(tmp_path)
    clean = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"legacy-clean",
        camera=_camera(),
    )
    measurement = capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"legacy-measurement",
        camera=_camera(),
    )

    payload = capture.get(session.session_id).model_dump(mode="json")
    payload["views"][0].pop("active_clean_reference_frame_id", None)
    for frame in payload["frames"]:
        if frame["kind"] == "MEASUREMENT":
            frame.pop("source_clean_reference_frame_id", None)

    migrated = CaptureSession.model_validate(payload)
    assert migrated.views[0].active_clean_reference_frame_id == clean.frame_id
    migrated_measurement = next(f for f in migrated.frames if f.frame_id == measurement.frame_id)
    assert migrated_measurement.source_clean_reference_frame_id == clean.frame_id


def test_recapture_is_rejected_after_view_acceptance(tmp_path: Path) -> None:
    _, _, _, capture, _, _, _, session = _fixture(tmp_path)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    capture.accept_view(session.session_id, view=CaptureViewType.FRONT)

    with pytest.raises(CaptureWorkflowError, match="explicitly reopened"):
        capture.recapture_clean_reference(
            session.session_id,
            view=CaptureViewType.FRONT,
            image_bytes=b"new-clean",
            camera=_camera(),
        )
