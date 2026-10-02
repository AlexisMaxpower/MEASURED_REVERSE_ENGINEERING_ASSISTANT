from pathlib import Path

import pytest

from mrea_capture import (
    CameraMetadata,
    CanonicalContractBuilder,
    CapturePlanService,
    CapturePreparationAction,
    CapturePreparationCaptureService,
    CapturePreparationGateError,
    CapturePreparationObservation,
    CaptureSessionService,
    CaptureViewType,
    FileSystemArtifactStore,
    FrameKind,
    JsonCaptureSessionRepository,
    PartContext,
    Project,
)


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=1280, height_px=960, device_model="test-phone")


def _ready(view: CaptureViewType = CaptureViewType.FRONT) -> CapturePreparationObservation:
    return CapturePreparationObservation(
        view=view,
        measurement_mat_ready=True,
        object_stable=True,
        background_clear=True,
        lighting_usable=True,
        features_unobstructed=True,
    )


def _session(tmp_path: Path):
    project = Project(name="Prepared capture", part=PartContext(part_type="bracket"))
    plan = CapturePlanService().create_plan(project)
    repository = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repository, store)
    session = capture.start(plan)
    gate = CapturePreparationCaptureService(capture)
    return project, capture, gate, session


def test_blocked_preparation_fails_before_capture_mutation(tmp_path: Path) -> None:
    _, capture, gate, session = _session(tmp_path)
    before = capture.get(session.session_id).model_dump(mode="json")
    blocked = _ready().model_copy(update={"background_clear": None})

    with pytest.raises(CapturePreparationGateError) as exc_info:
        gate.capture_clean_reference(
            session.session_id,
            observation=blocked,
            image_bytes=b"must-not-be-written",
            camera=_camera(),
        )

    after = capture.get(session.session_id).model_dump(mode="json")
    assert after == before
    assert exc_info.value.result.ready is False
    assert exc_info.value.result.next_action is CapturePreparationAction.CLEAR_BACKGROUND
    assert list(tmp_path.rglob("*.jpg")) == []


def test_ready_preparation_captures_clean_reference(tmp_path: Path) -> None:
    _, capture, gate, session = _session(tmp_path)

    result = gate.capture_clean_reference(
        session.session_id,
        observation=_ready(),
        image_bytes=b"clean-reference",
        camera=_camera(),
    )

    stored = capture.get(session.session_id)
    assert result.preparation.ready is True
    assert result.preparation.next_action is CapturePreparationAction.CAPTURE_CLEAN_REFERENCE
    assert result.frame.kind is FrameKind.CLEAN_REFERENCE
    assert stored.views[0].active_clean_reference_frame_id == result.frame.frame_id
    assert [frame.frame_id for frame in stored.frames] == [result.frame.frame_id]


def test_recapture_uses_same_preparation_gate_and_preserves_lineage(tmp_path: Path) -> None:
    _, capture, gate, session = _session(tmp_path)
    first = gate.capture_clean_reference(
        session.session_id,
        observation=_ready(),
        image_bytes=b"attempt-1",
        camera=_camera(),
    ).frame

    blocked = _ready().model_copy(update={"object_stable": False})
    with pytest.raises(CapturePreparationGateError):
        gate.recapture_clean_reference(
            session.session_id,
            observation=blocked,
            image_bytes=b"attempt-2-blocked",
            camera=_camera(),
        )

    unchanged = capture.get(session.session_id)
    assert len(unchanged.frames) == 1
    assert unchanged.views[0].active_clean_reference_frame_id == first.frame_id

    second = gate.recapture_clean_reference(
        session.session_id,
        observation=_ready(),
        image_bytes=b"attempt-2",
        camera=_camera(),
    ).frame
    stored = capture.get(session.session_id)

    assert second.supersedes_frame_id == first.frame_id
    assert stored.views[0].active_clean_reference_frame_id == second.frame_id
    assert [frame.frame_id for frame in stored.frames] == [first.frame_id, second.frame_id]


def test_preparation_gate_does_not_expand_canonical_capture_package(tmp_path: Path) -> None:
    project, capture, gate, session = _session(tmp_path)
    gate.capture_clean_reference(
        session.session_id,
        observation=_ready(),
        image_bytes=b"canonical-clean",
        camera=_camera(),
    )

    package = CanonicalContractBuilder.capture_package(
        project,
        capture.get(session.session_id),
    )

    assert package["schema_version"] == "mrea.capture-package.v1"
    assert "preparation" not in repr(package).lower()
