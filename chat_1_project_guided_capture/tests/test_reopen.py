from datetime import timedelta
from pathlib import Path

import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.guidance import (
    GuidedCaptureAction,
    GuidedCaptureBlockerCode,
    GuidedCaptureReadinessService,
)
from mrea_capture.models import CameraMetadata, CaptureViewStatus, CaptureViewType, PartContext, Project
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService, CaptureWorkflowError


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=640, height_px=480, device_model="FixtureCam")


def _fixture(tmp_path: Path):
    project = Project(name="Reopen fixture", part=PartContext(part_type="flat plate"))
    plan = CapturePlanService().create_plan(project)
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    clean = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"accepted-clean",
        camera=_camera(),
    )
    accepted = capture.accept_view(session.session_id, view=CaptureViewType.FRONT)
    return repo, store, capture, accepted, clean


def test_reopen_accepted_view_records_audit_event_and_requires_recapture(tmp_path: Path) -> None:
    _, _, capture, accepted, clean = _fixture(tmp_path)
    prior_accepted_at = accepted.views[0].accepted_at
    assert prior_accepted_at is not None
    assert accepted.completed_at is not None

    reopened = capture.reopen_view(
        accepted.session_id,
        view=CaptureViewType.FRONT,
        reason="Need a sharper reference before final handoff",
    )
    progress = reopened.views[0]

    assert progress.status is CaptureViewStatus.CAPTURED
    assert progress.accepted_at is None
    assert progress.recapture_required is True
    assert reopened.completed_at is None
    assert len(reopened.revision_events) == 1

    event = reopened.revision_events[0]
    assert event.view is CaptureViewType.FRONT
    assert event.reason == "Need a sharper reference before final handoff"
    assert event.previous_accepted_at == prior_accepted_at
    assert event.active_clean_reference_frame_id == clean.frame_id

    readiness = GuidedCaptureReadinessService().evaluate(reopened)
    assert readiness.next_action is GuidedCaptureAction.RECAPTURE_CLEAN_REFERENCE
    assert readiness.views[0].blockers == [
        GuidedCaptureBlockerCode.VIEW_REOPENED_RECAPTURE_REQUIRED
    ]


def test_reopened_view_cannot_be_reaccepted_before_fresh_clean_reference(tmp_path: Path) -> None:
    _, _, capture, accepted, _ = _fixture(tmp_path)
    capture.reopen_view(
        accepted.session_id,
        view=CaptureViewType.FRONT,
        reason="Revision requested",
    )

    with pytest.raises(CaptureWorkflowError, match="before a new clean reference"):
        capture.accept_view(accepted.session_id, view=CaptureViewType.FRONT)


def test_reopen_then_recapture_clears_gate_and_preserves_old_artifact(tmp_path: Path) -> None:
    _, store, capture, accepted, old_clean = _fixture(tmp_path)
    capture.reopen_view(
        accepted.session_id,
        view=CaptureViewType.FRONT,
        reason="Retake after physical setup change",
    )

    new_clean = capture.recapture_clean_reference(
        accepted.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"replacement-clean",
        camera=_camera(),
    )
    restored = capture.get(accepted.session_id)
    progress = restored.views[0]

    assert progress.recapture_required is False
    assert progress.active_clean_reference_frame_id == new_clean.frame_id
    assert new_clean.supersedes_frame_id == old_clean.frame_id
    assert store.get_bytes(old_clean.artifact) == b"accepted-clean"
    assert store.get_bytes(new_clean.artifact) == b"replacement-clean"
    assert len(restored.revision_events) == 1

    readiness = GuidedCaptureReadinessService().evaluate(restored)
    assert readiness.next_action is GuidedCaptureAction.RUN_CALIBRATION


def test_reopen_requires_accepted_view_and_nonblank_reason(tmp_path: Path) -> None:
    project = Project(name="Not accepted", part=PartContext(part_type="part"))
    plan = CapturePlanService().create_plan(project)
    repo = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
    )

    with pytest.raises(CaptureWorkflowError, match="not accepted"):
        capture.reopen_view(
            session.session_id,
            view=CaptureViewType.FRONT,
            reason="Premature reopen",
        )

    capture.accept_view(session.session_id, view=CaptureViewType.FRONT)
    with pytest.raises(CaptureWorkflowError, match="reason must be non-empty"):
        capture.reopen_view(
            session.session_id,
            view=CaptureViewType.FRONT,
            reason="   ",
        )


def test_reopen_timestamp_cannot_precede_original_acceptance(tmp_path: Path) -> None:
    _, _, capture, accepted, _ = _fixture(tmp_path)
    accepted_at = accepted.views[0].accepted_at
    assert accepted_at is not None

    with pytest.raises(CaptureWorkflowError, match="earlier than accepted_at"):
        capture.reopen_view(
            accepted.session_id,
            view=CaptureViewType.FRONT,
            reason="Invalid timestamp test",
            reopened_at=accepted_at - timedelta(seconds=1),
        )
