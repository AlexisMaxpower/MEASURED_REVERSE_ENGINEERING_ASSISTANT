from __future__ import annotations

from datetime import datetime
from uuid import UUID

from .artifacts import ArtifactStore
from .lineage import active_clean_reference
from .models import (
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureSession,
    CaptureViewProgress,
    CaptureViewStatus,
    CaptureViewType,
    MeasurementMatProfile,
)
from .quality import CaptureQualityAnalyzer, CaptureQualityError, CaptureQualityService
from .repositories import CaptureSessionRepository
from .services import CaptureSessionService


class CaptureQualityLifecycleError(CaptureQualityError):
    """Raised when quality evidence conflicts with the capture-view lifecycle."""


class CaptureQualityLifecycleService:
    """Synchronize diagnostic quality evidence with internal capture lifecycle state.

    This facade keeps quality diagnostic-only: it never creates physical measurement
    truth and never changes the canonical CapturePackage. It only synchronizes the
    Chat-1 internal view lifecycle around the active immutable clean reference.
    """

    def __init__(
        self,
        repository: CaptureSessionRepository,
        artifact_store: ArtifactStore,
        analyzer: CaptureQualityAnalyzer,
    ) -> None:
        self._repository = repository
        self._quality = CaptureQualityService(repository, artifact_store, analyzer)
        self._capture = CaptureSessionService(repository, artifact_store)

    def analyze_clean_reference(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        mat_profile: MeasurementMatProfile | None = None,
    ) -> CaptureQualityResult:
        session = self._repository.get(session_id)
        progress = self._progress_for(session, view)
        if progress.status is CaptureViewStatus.ACCEPTED:
            raise CaptureQualityLifecycleError(
                f"accepted view {view.value} must be reopened before quality reanalysis"
            )
        if progress.recapture_required:
            raise CaptureQualityLifecycleError(
                f"view {view.value} requires a fresh clean reference before quality analysis"
            )

        result = self._quality.analyze_clean_reference(
            session_id,
            view=view,
            mat_profile=mat_profile,
        )

        # Re-read after CaptureQualityService persists the result. This also makes a
        # repeated call a recovery path if a previous status save was interrupted.
        session = self._repository.get(session_id)
        progress = self._progress_for(session, view)
        active = active_clean_reference(session, view)
        if active is None or active.frame_id != result.source_frame_id:
            raise CaptureQualityLifecycleError(
                "quality result does not belong to the active clean-reference attempt"
            )

        target_status = (
            CaptureViewStatus.IN_PROGRESS
            if result.verdict is CaptureQualityVerdict.REJECT
            else CaptureViewStatus.CAPTURED
        )
        if progress.status is not target_status:
            progress.status = target_status
            if target_status is CaptureViewStatus.IN_PROGRESS:
                progress.accepted_at = None
                session.completed_at = None
            self._repository.save(session)
        return result

    def accept_view(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        accepted_at: datetime | None = None,
    ) -> CaptureSession:
        session = self._repository.get(session_id)
        active = active_clean_reference(session, view)
        if active is None:
            raise CaptureQualityLifecycleError(
                f"cannot accept {view.value} without an active clean reference"
            )

        matches = [
            item
            for item in session.quality_analyses
            if item.source_frame_id == active.frame_id
        ]
        if len(matches) > 1:
            raise CaptureQualityLifecycleError(
                f"active clean reference {active.frame_id} has multiple quality analyses"
            )
        if matches and matches[0].verdict is CaptureQualityVerdict.REJECT:
            raise CaptureQualityLifecycleError(
                f"cannot accept {view.value}: active clean reference quality is REJECT"
            )

        return self._capture.accept_view(
            session_id,
            view=view,
            accepted_at=accepted_at,
        )

    @staticmethod
    def _progress_for(
        session: CaptureSession,
        view: CaptureViewType,
    ) -> CaptureViewProgress:
        for progress in session.views:
            if progress.view is view:
                return progress
        raise CaptureQualityLifecycleError(f"view {view.value} is not part of capture session")
