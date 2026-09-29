from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .models import (
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureSession,
    CaptureViewStatus,
    CaptureViewType,
    FrameKind,
    StrictModel,
)


class GuidedCaptureError(RuntimeError):
    pass


class GuidedCaptureAction(StrEnum):
    CAPTURE_CLEAN_REFERENCE = "CAPTURE_CLEAN_REFERENCE"
    RUN_CALIBRATION = "RUN_CALIBRATION"
    ANALYZE_QUALITY = "ANALYZE_QUALITY"
    RESOLVE_QUALITY = "RESOLVE_QUALITY"
    CAPTURE_MEASUREMENT_FRAME = "CAPTURE_MEASUREMENT_FRAME"
    ACCEPT_VIEW = "ACCEPT_VIEW"
    COMPLETE = "COMPLETE"


class GuidedCaptureBlockerCode(StrEnum):
    CLEAN_REFERENCE_MISSING = "CLEAN_REFERENCE_MISSING"
    CALIBRATION_MISSING = "CALIBRATION_MISSING"
    QUALITY_ANALYSIS_MISSING = "QUALITY_ANALYSIS_MISSING"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    QUALITY_WARNING_REVIEW_REQUIRED = "QUALITY_WARNING_REVIEW_REQUIRED"
    MEASUREMENT_FRAME_MISSING = "MEASUREMENT_FRAME_MISSING"
    VIEW_NOT_ACCEPTED = "VIEW_NOT_ACCEPTED"


class GuidedCapturePolicy(StrictModel):
    """Internal guided-capture readiness policy; never physical measurement truth."""

    policy_version: str = "chat1.guided-capture.v1"
    require_calibration: bool = True
    require_quality_analysis: bool = True
    allow_quality_warn: bool = True
    require_measurement_frame: bool = True


class GuidedViewReadiness(StrictModel):
    view: CaptureViewType
    required: bool
    status: CaptureViewStatus
    ready_for_acceptance: bool
    action: GuidedCaptureAction
    blockers: list[GuidedCaptureBlockerCode] = Field(default_factory=list)
    clean_reference_frame_id: UUID | None = None
    calibration_id: UUID | None = None
    quality_analysis_id: UUID | None = None
    quality_verdict: CaptureQualityVerdict | None = None
    measurement_frame_count: int = Field(default=0, ge=0)


class GuidedCaptureReadiness(StrictModel):
    session_id: UUID
    policy_version: str
    complete: bool
    next_required_view: CaptureViewType | None = None
    next_action: GuidedCaptureAction
    required_views_remaining: list[CaptureViewType] = Field(default_factory=list)
    views: list[GuidedViewReadiness]


class GuidedCaptureReadinessService:
    """Derive deterministic next-action guidance from persisted capture evidence."""

    def __init__(self, policy: GuidedCapturePolicy | None = None) -> None:
        self.policy = policy or GuidedCapturePolicy()

    def evaluate(self, session: CaptureSession) -> GuidedCaptureReadiness:
        states = [self._evaluate_view(session, item.view) for item in session.views]
        remaining = [state.view for state in states if state.required and state.action is not GuidedCaptureAction.COMPLETE]

        if remaining:
            next_view = remaining[0]
            next_state = next(state for state in states if state.view is next_view)
            next_action = next_state.action
            complete = False
        else:
            next_view = None
            next_action = GuidedCaptureAction.COMPLETE
            complete = True

        return GuidedCaptureReadiness(
            session_id=session.session_id,
            policy_version=self.policy.policy_version,
            complete=complete,
            next_required_view=next_view,
            next_action=next_action,
            required_views_remaining=remaining,
            views=states,
        )

    def _evaluate_view(self, session: CaptureSession, view: CaptureViewType) -> GuidedViewReadiness:
        progress = next((item for item in session.views if item.view is view), None)
        if progress is None:
            raise GuidedCaptureError(f"view {view.value} is not part of the capture session")

        clean_frames = [
            frame
            for frame in session.frames
            if frame.view is view and frame.kind is FrameKind.CLEAN_REFERENCE
        ]
        if len(clean_frames) > 1:
            raise GuidedCaptureError(f"view {view.value} has multiple clean reference frames")
        clean = clean_frames[0] if clean_frames else None

        calibrations = [item for item in session.calibrations if item.view is view]
        if len(calibrations) > 1:
            raise GuidedCaptureError(f"view {view.value} has multiple calibrations")
        calibration = calibrations[0] if calibrations else None

        quality: CaptureQualityResult | None = None
        if clean is not None:
            quality_matches = [
                item for item in session.quality_analyses if item.source_frame_id == clean.frame_id
            ]
            if len(quality_matches) > 1:
                raise GuidedCaptureError(
                    f"clean reference {clean.frame_id} has multiple quality analyses"
                )
            quality = quality_matches[0] if quality_matches else None

        measurement_count = sum(
            1
            for frame in session.frames
            if frame.view is view and frame.kind is FrameKind.MEASUREMENT
        )

        action, blockers, ready = self._next_action(
            accepted=progress.status is CaptureViewStatus.ACCEPTED,
            clean_present=clean is not None,
            calibration_present=calibration is not None,
            quality=quality,
            measurement_count=measurement_count,
        )

        return GuidedViewReadiness(
            view=view,
            required=progress.required,
            status=progress.status,
            ready_for_acceptance=ready,
            action=action,
            blockers=blockers,
            clean_reference_frame_id=clean.frame_id if clean else None,
            calibration_id=calibration.calibration_id if calibration else None,
            quality_analysis_id=quality.analysis_id if quality else None,
            quality_verdict=quality.verdict if quality else None,
            measurement_frame_count=measurement_count,
        )

    def _next_action(
        self,
        *,
        accepted: bool,
        clean_present: bool,
        calibration_present: bool,
        quality: CaptureQualityResult | None,
        measurement_count: int,
    ) -> tuple[GuidedCaptureAction, list[GuidedCaptureBlockerCode], bool]:
        if accepted:
            return GuidedCaptureAction.COMPLETE, [], True

        if not clean_present:
            return (
                GuidedCaptureAction.CAPTURE_CLEAN_REFERENCE,
                [GuidedCaptureBlockerCode.CLEAN_REFERENCE_MISSING],
                False,
            )

        if self.policy.require_calibration and not calibration_present:
            return (
                GuidedCaptureAction.RUN_CALIBRATION,
                [GuidedCaptureBlockerCode.CALIBRATION_MISSING],
                False,
            )

        if self.policy.require_quality_analysis and quality is None:
            return (
                GuidedCaptureAction.ANALYZE_QUALITY,
                [GuidedCaptureBlockerCode.QUALITY_ANALYSIS_MISSING],
                False,
            )

        if quality is not None and quality.verdict is CaptureQualityVerdict.REJECT:
            return (
                GuidedCaptureAction.RESOLVE_QUALITY,
                [GuidedCaptureBlockerCode.QUALITY_REJECTED],
                False,
            )

        if (
            quality is not None
            and quality.verdict is CaptureQualityVerdict.WARN
            and not self.policy.allow_quality_warn
        ):
            return (
                GuidedCaptureAction.RESOLVE_QUALITY,
                [GuidedCaptureBlockerCode.QUALITY_WARNING_REVIEW_REQUIRED],
                False,
            )

        if self.policy.require_measurement_frame and measurement_count == 0:
            return (
                GuidedCaptureAction.CAPTURE_MEASUREMENT_FRAME,
                [GuidedCaptureBlockerCode.MEASUREMENT_FRAME_MISSING],
                False,
            )

        return (
            GuidedCaptureAction.ACCEPT_VIEW,
            [GuidedCaptureBlockerCode.VIEW_NOT_ACCEPTED],
            True,
        )
