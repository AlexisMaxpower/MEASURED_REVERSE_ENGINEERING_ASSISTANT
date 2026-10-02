from pathlib import Path

import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.guidance import GuidedCaptureAction, GuidedCaptureError
from mrea_capture.models import CameraMetadata, CaptureViewType, PartContext, Project
from mrea_capture.preparation import (
    CapturePreparationCheckCode,
    CapturePreparationObservation,
)
from mrea_capture.prepared_guidance import (
    PreparationAwareGuidedAction,
    PreparationAwareGuidedCaptureReadinessService,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=640, height_px=480)


def _ready(view: CaptureViewType) -> CapturePreparationObservation:
    return CapturePreparationObservation(
        view=view,
        measurement_mat_ready=True,
        object_stable=True,
        background_clear=True,
        lighting_usable=True,
        features_unobstructed=True,
    )


def _session(tmp_path: Path, *, views=(CaptureViewType.FRONT,)):
    project = Project(name="Prepared guidance fixture", part=PartContext(part_type="flat plate"))
    plan = CapturePlanService().create_plan(project, views=views)
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    return project, capture, session


def test_missing_preparation_fails_closed_before_capture_guidance(tmp_path: Path) -> None:
    _, capture, session = _session(tmp_path)

    result = PreparationAwareGuidedCaptureReadinessService().evaluate(
        capture.get(session.session_id)
    )

    assert result.next_required_view is CaptureViewType.FRONT
    assert result.guided.next_action is GuidedCaptureAction.CAPTURE_CLEAN_REFERENCE
    assert result.next_action is PreparationAwareGuidedAction.CHECK_PREPARATION
    assert result.preparation_required is True
    assert result.preparation is None


def test_failed_preparation_surfaces_deterministic_corrective_action(tmp_path: Path) -> None:
    _, capture, session = _session(tmp_path)
    observation = _ready(CaptureViewType.FRONT).model_copy(
        update={"background_clear": False}
    )

    result = PreparationAwareGuidedCaptureReadinessService().evaluate(
        capture.get(session.session_id), observation=observation
    )

    assert result.next_action is PreparationAwareGuidedAction.CLEAR_BACKGROUND
    assert result.preparation is not None
    assert result.preparation.ready is False
    assert [item.code for item in result.preparation.findings] == [
        CapturePreparationCheckCode.BACKGROUND_CLEAR
    ]


def test_ready_preparation_allows_initial_clean_reference_action(tmp_path: Path) -> None:
    _, capture, session = _session(tmp_path)

    result = PreparationAwareGuidedCaptureReadinessService().evaluate(
        capture.get(session.session_id), observation=_ready(CaptureViewType.FRONT)
    )

    assert result.next_action is PreparationAwareGuidedAction.CAPTURE_CLEAN_REFERENCE
    assert result.preparation_required is True
    assert result.preparation is not None
    assert result.preparation.ready is True


def test_ready_preparation_preserves_recapture_semantics(tmp_path: Path) -> None:
    _, capture, session = _session(tmp_path)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    capture.accept_view(session.session_id, view=CaptureViewType.FRONT)
    capture.reopen_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        reason="operator requested a new attempt",
    )

    result = PreparationAwareGuidedCaptureReadinessService().evaluate(
        capture.get(session.session_id), observation=_ready(CaptureViewType.FRONT)
    )

    assert result.guided.next_action is GuidedCaptureAction.RECAPTURE_CLEAN_REFERENCE
    assert result.next_action is PreparationAwareGuidedAction.RECAPTURE_CLEAN_REFERENCE
    assert result.preparation is not None
    assert result.preparation.ready is True


def test_preparation_observation_must_match_current_guided_view(tmp_path: Path) -> None:
    _, capture, session = _session(
        tmp_path,
        views=(CaptureViewType.FRONT, CaptureViewType.RIGHT),
    )

    with pytest.raises(GuidedCaptureError, match="expected FRONT, got RIGHT"):
        PreparationAwareGuidedCaptureReadinessService().evaluate(
            capture.get(session.session_id),
            observation=_ready(CaptureViewType.RIGHT),
        )


def test_preparation_does_not_gate_non_capture_actions(tmp_path: Path) -> None:
    _, capture, session = _session(tmp_path)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )

    result = PreparationAwareGuidedCaptureReadinessService().evaluate(
        capture.get(session.session_id)
    )

    assert result.guided.next_action is GuidedCaptureAction.RUN_CALIBRATION
    assert result.next_action is PreparationAwareGuidedAction.RUN_CALIBRATION
    assert result.preparation_required is False
    assert result.preparation is None


def test_composed_guidance_is_deterministic_read_only_and_canonical_neutral(tmp_path: Path) -> None:
    project, capture, session = _session(tmp_path)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )
    capture.accept_view(session.session_id, view=CaptureViewType.FRONT)
    capture.reopen_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        reason="repeat capture",
    )

    current = capture.get(session.session_id)
    before_session = current.model_dump(mode="json")
    before_contract = CanonicalContractBuilder.capture_package(project, current)
    service = PreparationAwareGuidedCaptureReadinessService()
    observation = _ready(CaptureViewType.FRONT)

    first = service.evaluate(current, observation=observation)
    second = service.evaluate(capture.get(session.session_id), observation=observation)

    assert first == second
    assert capture.get(session.session_id).model_dump(mode="json") == before_session
    assert CanonicalContractBuilder.capture_package(
        project, capture.get(session.session_id)
    ) == before_contract
