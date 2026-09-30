from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .models import (
    CaptureQualityVerdict,
    CaptureSession,
    CaptureViewStatus,
    CaptureViewType,
    FrameKind,
    StrictModel,
)


class CaptureAttemptHistoryError(RuntimeError):
    pass


class CaptureAttemptSnapshot(StrictModel):
    attempt_number: int = Field(ge=1)
    clean_reference_frame_id: UUID
    artifact_id: UUID
    artifact_sha256: str
    captured_at: datetime
    supersedes_frame_id: UUID | None = None
    superseded_by_frame_id: UUID | None = None
    active: bool = False
    accepted_at: datetime | None = None
    revision_event_ids: list[UUID] = Field(default_factory=list)
    calibration_id: UUID | None = None
    quality_analysis_id: UUID | None = None
    quality_verdict: CaptureQualityVerdict | None = None
    rectified_reference_id: UUID | None = None
    measurement_frame_ids: list[UUID] = Field(default_factory=list)


class CaptureViewAttemptHistory(StrictModel):
    session_id: UUID
    view: CaptureViewType
    status: CaptureViewStatus
    recapture_required: bool
    active_clean_reference_frame_id: UUID | None = None
    active_attempt_number: int | None = Field(default=None, ge=1)
    attempts: list[CaptureAttemptSnapshot] = Field(default_factory=list)


class CaptureAttemptHistoryService:
    """Project immutable capture evidence into one deterministic attempt chain per view."""

    def project_view(
        self,
        session: CaptureSession,
        view: CaptureViewType,
    ) -> CaptureViewAttemptHistory:
        progress = next((item for item in session.views if item.view is view), None)
        if progress is None:
            raise CaptureAttemptHistoryError(f"view {view.value} is not part of the capture session")

        clean_frames = [
            frame
            for frame in session.frames
            if frame.view is view and frame.kind is FrameKind.CLEAN_REFERENCE
        ]
        ordered = self._ordered_clean_lineage(clean_frames, view=view)

        calibration_by_source = {
            item.source_frame_id: item
            for item in session.calibrations
            if item.view is view
        }
        quality_by_source = {
            item.source_frame_id: item
            for item in session.quality_analyses
            if item.view is view
        }
        rectification_by_source = {
            item.source_frame_id: item
            for item in session.rectified_references
            if item.view is view
        }
        measurements_by_source: dict[UUID, list[UUID]] = {}
        for frame in session.frames:
            if frame.view is not view or frame.kind is not FrameKind.MEASUREMENT:
                continue
            source_id = frame.source_clean_reference_frame_id
            if source_id is None:
                raise CaptureAttemptHistoryError(
                    f"measurement frame {frame.frame_id} has no clean-reference provenance"
                )
            measurements_by_source.setdefault(source_id, []).append(frame.frame_id)

        revisions_by_source: dict[UUID, list] = {}
        for event in session.revision_events:
            if event.view is view:
                revisions_by_source.setdefault(
                    event.active_clean_reference_frame_id, []
                ).append(event)

        successor_by_source = {
            frame.supersedes_frame_id: frame.frame_id
            for frame in ordered
            if frame.supersedes_frame_id is not None
        }

        snapshots: list[CaptureAttemptSnapshot] = []
        for index, frame in enumerate(ordered, start=1):
            calibration = calibration_by_source.get(frame.frame_id)
            quality = quality_by_source.get(frame.frame_id)
            rectification = rectification_by_source.get(frame.frame_id)
            revisions = sorted(
                revisions_by_source.get(frame.frame_id, []),
                key=lambda event: (event.reopened_at, str(event.revision_id)),
            )

            accepted_at = None
            if revisions:
                accepted_at = revisions[-1].previous_accepted_at
            if progress.active_clean_reference_frame_id == frame.frame_id and progress.accepted_at:
                accepted_at = progress.accepted_at

            snapshots.append(
                CaptureAttemptSnapshot(
                    attempt_number=index,
                    clean_reference_frame_id=frame.frame_id,
                    artifact_id=frame.artifact.artifact_id,
                    artifact_sha256=frame.artifact.sha256,
                    captured_at=frame.captured_at,
                    supersedes_frame_id=frame.supersedes_frame_id,
                    superseded_by_frame_id=successor_by_source.get(frame.frame_id),
                    active=progress.active_clean_reference_frame_id == frame.frame_id,
                    accepted_at=accepted_at,
                    revision_event_ids=[event.revision_id for event in revisions],
                    calibration_id=calibration.calibration_id if calibration else None,
                    quality_analysis_id=quality.analysis_id if quality else None,
                    quality_verdict=quality.verdict if quality else None,
                    rectified_reference_id=(
                        rectification.rectified_reference_id if rectification else None
                    ),
                    measurement_frame_ids=measurements_by_source.get(frame.frame_id, []),
                )
            )

        active_attempt_number = next(
            (item.attempt_number for item in snapshots if item.active),
            None,
        )
        return CaptureViewAttemptHistory(
            session_id=session.session_id,
            view=view,
            status=progress.status,
            recapture_required=progress.recapture_required,
            active_clean_reference_frame_id=progress.active_clean_reference_frame_id,
            active_attempt_number=active_attempt_number,
            attempts=snapshots,
        )

    def project_session(self, session: CaptureSession) -> list[CaptureViewAttemptHistory]:
        return [self.project_view(session, item.view) for item in session.views]

    @staticmethod
    def _ordered_clean_lineage(clean_frames, *, view: CaptureViewType):
        if not clean_frames:
            return []

        by_id = {frame.frame_id: frame for frame in clean_frames}
        roots = [frame for frame in clean_frames if frame.supersedes_frame_id is None]
        if len(roots) != 1:
            raise CaptureAttemptHistoryError(
                f"view {view.value} requires exactly one clean-reference lineage root"
            )

        successor_by_id: dict[UUID, object] = {}
        for frame in clean_frames:
            predecessor_id = frame.supersedes_frame_id
            if predecessor_id is None:
                continue
            if predecessor_id not in by_id:
                raise CaptureAttemptHistoryError(
                    f"clean frame {frame.frame_id} references missing predecessor {predecessor_id}"
                )
            if predecessor_id in successor_by_id:
                raise CaptureAttemptHistoryError(
                    f"clean-reference lineage branches at frame {predecessor_id}"
                )
            successor_by_id[predecessor_id] = frame

        ordered = []
        seen: set[UUID] = set()
        current = roots[0]
        while current is not None:
            if current.frame_id in seen:
                raise CaptureAttemptHistoryError(
                    f"clean-reference lineage cycle detected for view {view.value}"
                )
            seen.add(current.frame_id)
            ordered.append(current)
            current = successor_by_id.get(current.frame_id)

        if len(ordered) != len(clean_frames):
            raise CaptureAttemptHistoryError(
                f"clean-reference lineage is disconnected for view {view.value}"
            )
        return ordered
