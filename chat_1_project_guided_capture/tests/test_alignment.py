from pathlib import Path

import pytest

from mrea_capture.alignment import (
    CaptureAlignmentAction,
    CaptureAlignmentError,
    CaptureAlignmentPolicy,
    CaptureAlignmentReasonCode,
    CaptureAlignmentService,
    CaptureAlignmentSeverity,
    CaptureAlignmentVerdict,
    RussianCaptureAlignmentGuidanceAdapter,
)
from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureViewType,
    PartContext,
    Project,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=640, height_px=480, device_model="fixture-camera")


def _fixture(
    tmp_path: Path,
    *,
    homography: list[float] | None = None,
):
    project = Project(name="Alignment fixture", part=PartContext(part_type="flat plate"))
    plan = CapturePlanService().create_plan(project, views=(CaptureViewType.FRONT,))
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    frame = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-reference",
        camera=_camera(),
    )
    if homography is not None:
        stored = capture.get(session.session_id)
        stored.calibrations.append(
            CalibrationResult(
                view=CaptureViewType.FRONT,
                source_frame_id=frame.frame_id,
                mat_id="MAT-A4-V1",
                homography=homography,
                detected_marker_count=10,
                detected_charuco_corner_count=20,
                reprojection_rmse_mm=0.1,
            )
        )
        repo.save(stored)
    return project, repo, capture, session.session_id


def test_frontoparallel_affine_alignment_is_accepted(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.1, 0, 0, 0, 1],
    )

    result = CaptureAlignmentService().evaluate(
        capture.get(session_id),
        view=CaptureViewType.FRONT,
    )

    assert result.verdict is CaptureAlignmentVerdict.ACCEPT
    assert result.next_action is CaptureAlignmentAction.CONTINUE_CAPTURE_WORKFLOW
    assert result.findings == []
    assert result.metrics.camera_tilt_proxy == pytest.approx(0.0)
    assert result.metrics.perspective_scale_ratio == pytest.approx(1.0)


def test_anisotropic_mapping_reports_camera_tilt_risk(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.04, 0, 0, 0, 1],
    )

    result = CaptureAlignmentService().evaluate(
        capture.get(session_id),
        view=CaptureViewType.FRONT,
    )

    assert result.verdict is CaptureAlignmentVerdict.REJECT
    assert result.next_action is CaptureAlignmentAction.REALIGN_CAMERA_PERPENDICULAR
    assert len(result.findings) == 1
    assert result.findings[0].code is CaptureAlignmentReasonCode.CAMERA_TILT_RISK
    assert result.findings[0].severity is CaptureAlignmentSeverity.REJECT
    assert result.metrics.camera_tilt_proxy == pytest.approx(0.6)
    assert result.metrics.perspective_scale_ratio == pytest.approx(1.0)


def test_projective_denominator_reports_perspective_distortion(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.1, 0, 0.002, 0, 1],
    )
    service = CaptureAlignmentService(
        CaptureAlignmentPolicy(check_camera_tilt=False)
    )

    result = service.evaluate(capture.get(session_id), view=CaptureViewType.FRONT)

    assert result.verdict is CaptureAlignmentVerdict.REJECT
    assert result.next_action is CaptureAlignmentAction.REDUCE_PERSPECTIVE_DISTORTION
    assert len(result.findings) == 1
    assert result.findings[0].code is CaptureAlignmentReasonCode.PERSPECTIVE_DISTORTION_RISK
    assert result.findings[0].severity is CaptureAlignmentSeverity.REJECT
    assert result.metrics.perspective_scale_ratio > 2.0


def test_moderate_perspective_is_actionable_warning(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.1, 0, 0.0006, 0, 1],
    )
    service = CaptureAlignmentService(
        CaptureAlignmentPolicy(check_camera_tilt=False)
    )

    result = service.evaluate(capture.get(session_id), view=CaptureViewType.FRONT)

    assert result.verdict is CaptureAlignmentVerdict.WARN
    assert result.next_action is CaptureAlignmentAction.REDUCE_PERSPECTIVE_DISTORTION
    assert len(result.findings) == 1
    assert result.findings[0].severity is CaptureAlignmentSeverity.WARN
    messages = RussianCaptureAlignmentGuidanceAdapter.messages(result)
    assert len(messages) == 1
    assert "Перспективное" in messages[0]


def test_alignment_fails_closed_without_active_calibration(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(tmp_path)

    with pytest.raises(CaptureAlignmentError, match="requires calibration"):
        CaptureAlignmentService().evaluate(
            capture.get(session_id),
            view=CaptureViewType.FRONT,
        )


def test_alignment_ignores_stale_calibration_after_recapture(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.1, 0, 0, 0, 1],
    )
    capture.recapture_clean_reference(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"new-clean-reference",
        camera=_camera(),
    )

    with pytest.raises(CaptureAlignmentError, match="requires calibration"):
        CaptureAlignmentService().evaluate(
            capture.get(session_id),
            view=CaptureViewType.FRONT,
        )


def test_alignment_rejects_homography_pole_crossing_source_frame(tmp_path: Path) -> None:
    _, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.1, 0, -0.002, 0, 1],
    )

    with pytest.raises(CaptureAlignmentError, match="denominator changes sign"):
        CaptureAlignmentService().evaluate(
            capture.get(session_id),
            view=CaptureViewType.FRONT,
        )


def test_alignment_is_deterministic_read_only_and_canonical_neutral(tmp_path: Path) -> None:
    project, _, capture, session_id = _fixture(
        tmp_path,
        homography=[0.1, 0, 0, 0, 0.1, 0, 0, 0, 1],
    )
    before_session = capture.get(session_id).model_dump(mode="json")
    before_package = CanonicalContractBuilder.capture_package(
        project,
        capture.get(session_id),
    )
    service = CaptureAlignmentService()

    first = service.evaluate(capture.get(session_id), view=CaptureViewType.FRONT)
    second = service.evaluate(capture.get(session_id), view=CaptureViewType.FRONT)

    after_session = capture.get(session_id).model_dump(mode="json")
    after_package = CanonicalContractBuilder.capture_package(
        project,
        capture.get(session_id),
    )
    assert first == second
    assert first.alignment_id == second.alignment_id
    assert before_session == after_session
    assert before_package == after_package
    assert RussianCaptureAlignmentGuidanceAdapter.messages(first) == [
        "Положение камеры пригодно для продолжения capture workflow."
    ]
