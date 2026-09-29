from pathlib import Path
from uuid import UUID

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.guidance import (
    GuidedCaptureAction,
    GuidedCaptureBlockerCode,
    GuidedCapturePolicy,
    GuidedCaptureReadinessService,
)
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureQualityMetrics,
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureViewType,
    PartContext,
    Project,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=640, height_px=480)


def _accepted_quality(frame_id: UUID, view: CaptureViewType) -> CaptureQualityResult:
    return CaptureQualityResult(
        analysis_id=UUID("00000000-0000-0000-0000-000000000901"),
        source_frame_id=frame_id,
        view=view,
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


def _quality(frame_id: UUID, view: CaptureViewType, verdict: CaptureQualityVerdict) -> CaptureQualityResult:
    from mrea_capture.models import CaptureQualityFinding, QualityReasonCode, QualitySeverity

    findings = []
    if verdict is CaptureQualityVerdict.WARN:
        findings = [
            CaptureQualityFinding(
                code=QualityReasonCode.GLARE_RISK,
                severity=QualitySeverity.WARN,
                metric="glare_proxy_fraction",
                observed=0.01,
                threshold=0.005,
                comparison=">",
            )
        ]
    elif verdict is CaptureQualityVerdict.REJECT:
        findings = [
            CaptureQualityFinding(
                code=QualityReasonCode.BLUR,
                severity=QualitySeverity.REJECT,
                metric="laplacian_variance",
                observed=5,
                threshold=20,
                comparison="<",
            )
        ]
    return CaptureQualityResult(
        analysis_id=UUID("00000000-0000-0000-0000-000000000902") if verdict is not CaptureQualityVerdict.ACCEPT else UUID("00000000-0000-0000-0000-000000000903"),
        source_frame_id=frame_id,
        view=view,
        policy_version="test.quality.v1",
        verdict=verdict,
        metrics=CaptureQualityMetrics(
            laplacian_variance=5 if verdict is CaptureQualityVerdict.REJECT else 100,
            mean_luma=120,
            dark_clipped_fraction=0,
            bright_clipped_fraction=0,
            glare_proxy_fraction=0.01 if verdict is CaptureQualityVerdict.WARN else 0,
            edge_density=0.1,
            border_edge_ratio=0.1,
        ),
        findings=findings,
    )


def _calibration(frame_id: UUID, view: CaptureViewType) -> CalibrationResult:
    return CalibrationResult(
        view=view,
        source_frame_id=frame_id,
        mat_id="MAT-A4-V1",
        homography=[1, 0, 0, 0, 1, 0, 0, 0, 1],
        detected_marker_count=10,
        detected_charuco_corner_count=20,
        reprojection_rmse_mm=0.1,
    )


def _session(tmp_path: Path, *, views=(CaptureViewType.FRONT,)):
    project = Project(name="Guided fixture", part=PartContext(part_type="flat plate"))
    plan = CapturePlanService().create_plan(project, views=views)
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    return project, repo, capture, session


def test_guided_readiness_progresses_through_expected_actions(tmp_path: Path) -> None:
    _, repo, capture, session = _session(tmp_path)
    guidance = GuidedCaptureReadinessService()

    initial = guidance.evaluate(capture.get(session.session_id))
    assert initial.next_action is GuidedCaptureAction.CAPTURE_CLEAN_REFERENCE
    assert initial.required_views_remaining == [CaptureViewType.FRONT]

    frame = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    after_clean = guidance.evaluate(capture.get(session.session_id))
    assert after_clean.next_action is GuidedCaptureAction.RUN_CALIBRATION

    stored = capture.get(session.session_id)
    stored.calibrations.append(_calibration(frame.frame_id, CaptureViewType.FRONT))
    repo.save(stored)
    after_calibration = guidance.evaluate(capture.get(session.session_id))
    assert after_calibration.next_action is GuidedCaptureAction.ANALYZE_QUALITY

    stored = capture.get(session.session_id)
    stored.quality_analyses.append(_accepted_quality(frame.frame_id, CaptureViewType.FRONT))
    repo.save(stored)
    after_quality = guidance.evaluate(capture.get(session.session_id))
    assert after_quality.next_action is GuidedCaptureAction.CAPTURE_MEASUREMENT_FRAME

    capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement",
        camera=_camera(),
    )
    ready = guidance.evaluate(capture.get(session.session_id))
    assert ready.next_action is GuidedCaptureAction.ACCEPT_VIEW
    assert ready.views[0].ready_for_acceptance is True
    assert ready.views[0].blockers == [GuidedCaptureBlockerCode.VIEW_NOT_ACCEPTED]

    capture.accept_view(session.session_id, view=CaptureViewType.FRONT)
    complete = guidance.evaluate(capture.get(session.session_id))
    assert complete.complete is True
    assert complete.next_required_view is None
    assert complete.next_action is GuidedCaptureAction.COMPLETE


def test_rejected_quality_blocks_progression(tmp_path: Path) -> None:
    _, repo, capture, session = _session(tmp_path)
    frame = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    stored = capture.get(session.session_id)
    stored.calibrations.append(_calibration(frame.frame_id, CaptureViewType.FRONT))
    stored.quality_analyses.append(_quality(frame.frame_id, CaptureViewType.FRONT, CaptureQualityVerdict.REJECT))
    repo.save(stored)

    result = GuidedCaptureReadinessService().evaluate(capture.get(session.session_id))
    assert result.next_action is GuidedCaptureAction.RESOLVE_QUALITY
    assert result.views[0].blockers == [GuidedCaptureBlockerCode.QUALITY_REJECTED]
    assert result.views[0].ready_for_acceptance is False


def test_quality_warning_policy_is_explicit(tmp_path: Path) -> None:
    _, repo, capture, session = _session(tmp_path)
    frame = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    stored = capture.get(session.session_id)
    stored.calibrations.append(_calibration(frame.frame_id, CaptureViewType.FRONT))
    stored.quality_analyses.append(_quality(frame.frame_id, CaptureViewType.FRONT, CaptureQualityVerdict.WARN))
    repo.save(stored)

    permissive = GuidedCaptureReadinessService().evaluate(capture.get(session.session_id))
    strict = GuidedCaptureReadinessService(
        GuidedCapturePolicy(allow_quality_warn=False)
    ).evaluate(capture.get(session.session_id))

    assert permissive.next_action is GuidedCaptureAction.CAPTURE_MEASUREMENT_FRAME
    assert strict.next_action is GuidedCaptureAction.RESOLVE_QUALITY
    assert strict.views[0].blockers == [GuidedCaptureBlockerCode.QUALITY_WARNING_REVIEW_REQUIRED]


def test_optional_view_does_not_block_required_completion(tmp_path: Path) -> None:
    _, repo, capture, session = _session(
        tmp_path,
        views=(CaptureViewType.FRONT, CaptureViewType.OPTIONAL_3Q),
    )
    frame = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    stored = capture.get(session.session_id)
    stored.calibrations.append(_calibration(frame.frame_id, CaptureViewType.FRONT))
    stored.quality_analyses.append(_accepted_quality(frame.frame_id, CaptureViewType.FRONT))
    repo.save(stored)
    capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement",
        camera=_camera(),
    )
    capture.accept_view(session.session_id, view=CaptureViewType.FRONT)

    result = GuidedCaptureReadinessService().evaluate(capture.get(session.session_id))
    assert result.complete is True
    assert result.next_action is GuidedCaptureAction.COMPLETE
    assert result.required_views_remaining == []
    optional = next(item for item in result.views if item.view is CaptureViewType.OPTIONAL_3Q)
    assert optional.required is False
    assert optional.action is GuidedCaptureAction.CAPTURE_CLEAN_REFERENCE


def test_guidance_is_deterministic_and_does_not_mutate_session(tmp_path: Path) -> None:
    _, _, capture, session = _session(tmp_path)
    before = capture.get(session.session_id).model_dump(mode="json")
    service = GuidedCaptureReadinessService()

    first = service.evaluate(capture.get(session.session_id))
    second = service.evaluate(capture.get(session.session_id))
    after = capture.get(session.session_id).model_dump(mode="json")

    assert first == second
    assert before == after


def test_guidance_does_not_change_canonical_capture_package(tmp_path: Path) -> None:
    project, _, capture, session = _session(tmp_path)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    current = capture.get(session.session_id)
    before = CanonicalContractBuilder.capture_package(project, current)

    GuidedCaptureReadinessService().evaluate(current)

    after = CanonicalContractBuilder.capture_package(
        project, capture.get(session.session_id)
    )
    assert before == after
