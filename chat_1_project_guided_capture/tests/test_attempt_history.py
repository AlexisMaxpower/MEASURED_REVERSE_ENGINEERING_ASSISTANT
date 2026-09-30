from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.calibration import CalibrationService
from mrea_capture.history import CaptureAttemptHistoryError, CaptureAttemptHistoryService
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureQualityMetrics,
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureSession,
    CaptureViewType,
    MeasurementMatProfile,
    PartContext,
    Project,
)
from mrea_capture.quality import CaptureQualityService
from mrea_capture.rectification import RectificationService, RectifiedRaster
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


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
            analysis_id=uuid5(NAMESPACE_URL, f"test:history:quality:{source_frame_id}"),
            source_frame_id=source_frame_id,
            view=view,
            calibration_id=calibration.calibration_id if calibration else None,
            mat_id=mat_profile.mat_id if mat_profile else calibration.mat_id if calibration else None,
            policy_version="test.history.v1",
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
    project = Project(name="History fixture", part=PartContext(part_type="plate"))
    plan = CapturePlanService().create_plan(project)
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    calibration = CalibrationService(repo, store, _Detector())
    quality = CaptureQualityService(repo, store, _Analyzer())
    rectification = RectificationService(repo, store, _Normalizer())
    return repo, capture, calibration, quality, rectification, session


def _complete_attempt(capture, calibration, quality, rectification, session_id, clean_bytes, measurement_bytes):
    clean = capture.capture_clean_reference(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=clean_bytes,
        camera=_camera(),
    )
    cal = calibration.calibrate_view(session_id, view=CaptureViewType.FRONT, profile=_profile())
    q = quality.analyze_clean_reference(session_id, view=CaptureViewType.FRONT, mat_profile=_profile())
    measurement = capture.capture_measurement_frame(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=measurement_bytes,
        camera=_camera(),
    )
    rectified = rectification.rectify_view(
        session_id,
        view=CaptureViewType.FRONT,
        profile=_profile(),
    )
    return clean, cal, q, measurement, rectified


def test_history_projects_single_active_attempt_without_mutating_session(tmp_path: Path) -> None:
    repo, capture, calibration, quality, rectification, session = _fixture(tmp_path)
    clean, cal, q, measurement, rectified = _complete_attempt(
        capture,
        calibration,
        quality,
        rectification,
        session.session_id,
        b"clean-v1",
        b"measurement-v1",
    )
    before = repo.get(session.session_id).model_dump(mode="json")

    history = CaptureAttemptHistoryService().project_view(
        repo.get(session.session_id), CaptureViewType.FRONT
    )

    assert history.active_attempt_number == 1
    assert history.active_clean_reference_frame_id == clean.frame_id
    assert len(history.attempts) == 1
    attempt = history.attempts[0]
    assert attempt.active is True
    assert attempt.clean_reference_frame_id == clean.frame_id
    assert attempt.calibration_id == cal.calibration_id
    assert attempt.quality_analysis_id == q.analysis_id
    assert attempt.quality_verdict is CaptureQualityVerdict.ACCEPT
    assert attempt.rectified_reference_id == rectified.rectified_reference_id
    assert attempt.measurement_frame_ids == [measurement.frame_id]
    assert repo.get(session.session_id).model_dump(mode="json") == before


def test_history_preserves_attempt_evidence_across_reopen_and_recapture(tmp_path: Path) -> None:
    repo, capture, calibration, quality, rectification, session = _fixture(tmp_path)
    clean_v1, cal_v1, q_v1, measurement_v1, rect_v1 = _complete_attempt(
        capture,
        calibration,
        quality,
        rectification,
        session.session_id,
        b"clean-v1",
        b"measurement-v1",
    )
    accepted = capture.accept_view(session.session_id, view=CaptureViewType.FRONT)
    accepted_at = accepted.views[0].accepted_at
    assert accepted_at is not None
    reopened = capture.reopen_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        reason="Replace accepted reference",
    )
    revision = reopened.revision_events[0]

    clean_v2 = capture.recapture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-v2",
        camera=_camera(),
    )
    cal_v2 = calibration.calibrate_view(session.session_id, view=CaptureViewType.FRONT, profile=_profile())
    q_v2 = quality.analyze_clean_reference(session.session_id, view=CaptureViewType.FRONT, mat_profile=_profile())
    measurement_v2 = capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement-v2",
        camera=_camera(),
    )
    rect_v2 = rectification.rectify_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        profile=_profile(),
    )

    history = CaptureAttemptHistoryService().project_view(
        repo.get(session.session_id), CaptureViewType.FRONT
    )
    assert history.active_attempt_number == 2
    assert [item.clean_reference_frame_id for item in history.attempts] == [
        clean_v1.frame_id,
        clean_v2.frame_id,
    ]

    first, second = history.attempts
    assert first.active is False
    assert first.superseded_by_frame_id == clean_v2.frame_id
    assert first.accepted_at == accepted_at
    assert first.revision_event_ids == [revision.revision_id]
    assert first.calibration_id == cal_v1.calibration_id
    assert first.quality_analysis_id == q_v1.analysis_id
    assert first.rectified_reference_id == rect_v1.rectified_reference_id
    assert first.measurement_frame_ids == [measurement_v1.frame_id]

    assert second.active is True
    assert second.supersedes_frame_id == clean_v1.frame_id
    assert second.calibration_id == cal_v2.calibration_id
    assert second.quality_analysis_id == q_v2.analysis_id
    assert second.rectified_reference_id == rect_v2.rectified_reference_id
    assert second.measurement_frame_ids == [measurement_v2.frame_id]
    assert second.revision_event_ids == []


def test_history_projects_views_in_capture_plan_order(tmp_path: Path) -> None:
    project = Project(name="Multi-view", part=PartContext(part_type="plate"))
    plan = CapturePlanService().create_plan(
        project,
        views=[CaptureViewType.LEFT, CaptureViewType.FRONT, CaptureViewType.OPTIONAL_3Q],
    )
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"front",
        camera=_camera(),
    )

    histories = CaptureAttemptHistoryService().project_session(repo.get(session.session_id))
    assert [item.view for item in histories] == [
        CaptureViewType.LEFT,
        CaptureViewType.FRONT,
        CaptureViewType.OPTIONAL_3Q,
    ]
    assert histories[0].attempts == []
    assert histories[1].active_attempt_number == 1
    assert histories[2].attempts == []


def test_session_validation_rejects_disconnected_clean_reference_roots(tmp_path: Path) -> None:
    repo, capture, _, _, _, session = _fixture(tmp_path)
    first = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"first",
        camera=_camera(),
    )
    payload = repo.get(session.session_id).model_dump(mode="json")
    duplicate = dict(payload["frames"][0])
    duplicate["frame_id"] = "00000000-0000-0000-0000-000000000999"
    duplicate["artifact"] = dict(duplicate["artifact"])
    duplicate["artifact"]["artifact_id"] = "00000000-0000-0000-0000-000000000998"
    duplicate["supersedes_frame_id"] = None
    payload["frames"].append(duplicate)
    payload["views"][0]["active_clean_reference_frame_id"] = str(first.frame_id)

    corrupted = CaptureSession.model_validate(payload)
    with pytest.raises(CaptureAttemptHistoryError, match="exactly one clean-reference lineage root"):
        CaptureAttemptHistoryService().project_view(corrupted, CaptureViewType.FRONT)
