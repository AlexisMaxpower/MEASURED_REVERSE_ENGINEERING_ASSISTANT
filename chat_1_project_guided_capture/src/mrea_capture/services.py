from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from .artifacts import ArtifactStore
from .lineage import active_clean_reference
from .models import (
    CameraMetadata,
    CapturePlan,
    CapturePlanItem,
    CaptureSession,
    CaptureViewProgress,
    CaptureViewRevisionEvent,
    CaptureViewStatus,
    CaptureViewType,
    FrameKind,
    FrameRecord,
    PartContext,
    Project,
    ProjectStatus,
    utc_now,
)
from .repositories import CaptureSessionRepository, ProjectRepository


class CaptureWorkflowError(RuntimeError):
    pass


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def create_project(self, *, name: str, part: PartContext) -> Project:
        project = Project(name=name, part=part)
        self._repository.save(project)
        return project

    def get_project(self, project_id: UUID) -> Project:
        return self._repository.get(project_id)

    def archive_project(self, project_id: UUID, *, now: datetime | None = None) -> Project:
        project = self._repository.get(project_id)
        project.status = ProjectStatus.ARCHIVED
        project.updated_at = now or utc_now()
        self._repository.save(project)
        return project


class CapturePlanService:
    """Build deterministic local capture plans."""

    _RATIONALE = {
        CaptureViewType.FRONT: "Baseline orthographic reference required by Chat 1 acceptance criteria.",
        CaptureViewType.LEFT: "User-requested left-side coverage.",
        CaptureViewType.RIGHT: "User-requested right-side coverage.",
        CaptureViewType.TOP: "User-requested top coverage.",
        CaptureViewType.BOTTOM: "User-requested bottom coverage.",
        CaptureViewType.REAR: "User-requested rear coverage.",
        CaptureViewType.DETAIL_A: "User-requested detail coverage A.",
        CaptureViewType.DETAIL_B: "User-requested detail coverage B.",
        CaptureViewType.OPTIONAL_3Q: "Optional three-quarter context view.",
    }

    def create_plan(
        self,
        project: Project,
        *,
        views: Iterable[CaptureViewType] | None = None,
    ) -> CapturePlan:
        requested = list(views) if views is not None else [CaptureViewType.FRONT]
        if not requested:
            requested = [CaptureViewType.FRONT]

        ordered_unique: list[CaptureViewType] = []
        seen: set[CaptureViewType] = set()
        for view in requested:
            if view not in seen:
                ordered_unique.append(view)
                seen.add(view)

        items = [
            CapturePlanItem(
                sequence=index,
                view=view,
                required=view is not CaptureViewType.OPTIONAL_3Q,
                rationale=self._RATIONALE[view],
            )
            for index, view in enumerate(ordered_unique, start=1)
        ]
        return CapturePlan(project_id=project.project_id, items=items)


class CaptureSessionService:
    def __init__(
        self,
        repository: CaptureSessionRepository,
        artifact_store: ArtifactStore,
    ) -> None:
        self._repository = repository
        self._artifact_store = artifact_store

    def start(self, plan: CapturePlan) -> CaptureSession:
        session = CaptureSession(
            project_id=plan.project_id,
            plan_id=plan.plan_id,
            views=[
                CaptureViewProgress(view=item.view, required=item.required)
                for item in plan.items
            ],
        )
        self._repository.save(session)
        return session

    def get(self, session_id: UUID) -> CaptureSession:
        return self._repository.get(session_id)

    def capture_clean_reference(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        image_bytes: bytes,
        camera: CameraMetadata,
        captured_at: datetime | None = None,
        media_type: str = "image/jpeg",
        extension: str = ".jpg",
    ) -> FrameRecord:
        session = self._repository.get(session_id)
        progress = self._progress_for(session, view)
        if any(frame.view is view and frame.kind is FrameKind.CLEAN_REFERENCE for frame in session.frames):
            raise CaptureWorkflowError(
                f"clean reference history already exists for view {view.value}; use recapture_clean_reference"
            )

        frame = self._store_clean_reference(
            session,
            progress,
            view=view,
            image_bytes=image_bytes,
            camera=camera,
            captured_at=captured_at,
            media_type=media_type,
            extension=extension,
            supersedes_frame_id=None,
        )
        self._repository.save(session)
        return frame

    def recapture_clean_reference(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        image_bytes: bytes,
        camera: CameraMetadata,
        captured_at: datetime | None = None,
        media_type: str = "image/jpeg",
        extension: str = ".jpg",
    ) -> FrameRecord:
        """Create a new active clean-reference attempt without deleting prior evidence."""

        session = self._repository.get(session_id)
        progress = self._progress_for(session, view)
        if progress.status is CaptureViewStatus.ACCEPTED:
            raise CaptureWorkflowError(
                f"accepted view {view.value} must be explicitly reopened before recapture"
            )
        previous = active_clean_reference(session, view)
        if previous is None:
            raise CaptureWorkflowError(
                f"view {view.value} has no active clean reference to supersede"
            )

        frame = self._store_clean_reference(
            session,
            progress,
            view=view,
            image_bytes=image_bytes,
            camera=camera,
            captured_at=captured_at,
            media_type=media_type,
            extension=extension,
            supersedes_frame_id=previous.frame_id,
        )
        self._repository.save(session)
        return frame

    def _store_clean_reference(
        self,
        session: CaptureSession,
        progress: CaptureViewProgress,
        *,
        view: CaptureViewType,
        image_bytes: bytes,
        camera: CameraMetadata,
        captured_at: datetime | None,
        media_type: str,
        extension: str,
        supersedes_frame_id: UUID | None,
    ) -> FrameRecord:
        artifact = self._artifact_store.put_bytes(
            image_bytes,
            media_type=media_type,
            extension=extension,
        )
        timestamp = captured_at or utc_now()
        frame = FrameRecord(
            project_id=session.project_id,
            session_id=session.session_id,
            view=view,
            kind=FrameKind.CLEAN_REFERENCE,
            artifact=artifact,
            captured_at=timestamp,
            camera=camera,
            supersedes_frame_id=supersedes_frame_id,
        )
        session.frames.append(frame)
        progress.active_clean_reference_frame_id = frame.frame_id
        progress.status = CaptureViewStatus.CAPTURED
        progress.started_at = progress.started_at or timestamp
        progress.captured_at = timestamp
        progress.accepted_at = None
        progress.recapture_required = False
        return frame

    def capture_measurement_frame(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        image_bytes: bytes,
        camera: CameraMetadata,
        captured_at: datetime | None = None,
        media_type: str = "image/jpeg",
        extension: str = ".jpg",
    ) -> FrameRecord:
        session = self._repository.get(session_id)
        self._progress_for(session, view)
        clean = active_clean_reference(session, view)
        if clean is None:
            raise CaptureWorkflowError(
                f"measurement frame requires clean reference; no active clean reference for view {view.value}"
            )

        artifact = self._artifact_store.put_bytes(
            image_bytes,
            media_type=media_type,
            extension=extension,
        )
        frame = FrameRecord(
            project_id=session.project_id,
            session_id=session.session_id,
            view=view,
            kind=FrameKind.MEASUREMENT,
            artifact=artifact,
            captured_at=captured_at or utc_now(),
            camera=camera,
            source_clean_reference_frame_id=clean.frame_id,
        )
        session.frames.append(frame)
        self._repository.save(session)
        return frame

    def reopen_view(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        reason: str,
        reopened_at: datetime | None = None,
    ) -> CaptureSession:
        """Explicitly reopen an accepted view and require a fresh clean-reference attempt."""

        session = self._repository.get(session_id)
        progress = self._progress_for(session, view)
        if progress.status is not CaptureViewStatus.ACCEPTED or progress.accepted_at is None:
            raise CaptureWorkflowError(f"view {view.value} is not accepted and cannot be reopened")
        clean = active_clean_reference(session, view)
        if clean is None:
            raise CaptureWorkflowError(f"accepted view {view.value} has no active clean reference")
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise CaptureWorkflowError("reopen reason must be non-empty")

        timestamp = reopened_at or utc_now()
        if timestamp.tzinfo is None:
            raise CaptureWorkflowError("reopened_at must be timezone-aware")
        if timestamp < progress.accepted_at:
            raise CaptureWorkflowError("reopened_at cannot be earlier than accepted_at")

        session.revision_events.append(
            CaptureViewRevisionEvent(
                view=view,
                reason=normalized_reason,
                reopened_at=timestamp,
                previous_accepted_at=progress.accepted_at,
                active_clean_reference_frame_id=clean.frame_id,
            )
        )
        progress.status = CaptureViewStatus.CAPTURED
        progress.accepted_at = None
        progress.recapture_required = True
        session.completed_at = None
        self._repository.save(session)
        return session

    def accept_view(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        accepted_at: datetime | None = None,
    ) -> CaptureSession:
        session = self._repository.get(session_id)
        progress = self._progress_for(session, view)
        if active_clean_reference(session, view) is None:
            raise CaptureWorkflowError(f"cannot accept {view.value} without active clean reference")
        if progress.recapture_required:
            raise CaptureWorkflowError(
                f"cannot accept reopened view {view.value} before a new clean reference is captured"
            )

        timestamp = accepted_at or utc_now()
        progress.status = CaptureViewStatus.ACCEPTED
        progress.accepted_at = timestamp

        if all(
            (not item.required) or item.status is CaptureViewStatus.ACCEPTED
            for item in session.views
        ):
            session.completed_at = timestamp

        self._repository.save(session)
        return session

    @staticmethod
    def _progress_for(
        session: CaptureSession,
        view: CaptureViewType,
    ) -> CaptureViewProgress:
        for progress in session.views:
            if progress.view is view:
                return progress
        raise CaptureWorkflowError(f"view {view.value} is not part of capture plan")
