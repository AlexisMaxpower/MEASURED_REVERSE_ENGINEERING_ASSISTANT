from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from .guidance import (
    GuidedCaptureAction,
    GuidedCaptureError,
    GuidedCaptureReadiness,
    GuidedCaptureReadinessService,
)
from .models import CaptureSession, CaptureViewType, StrictModel
from .preparation import (
    CapturePreparationAction,
    CapturePreparationObservation,
    CapturePreparationResult,
    CapturePreparationService,
)


class PreparationAwareGuidedAction(StrEnum):
    """Single product-facing next action after composing guidance with preparation."""

    CHECK_PREPARATION = "CHECK_PREPARATION"
    FIX_MEASUREMENT_MAT = "FIX_MEASUREMENT_MAT"
    STABILIZE_OBJECT = "STABILIZE_OBJECT"
    CLEAR_BACKGROUND = "CLEAR_BACKGROUND"
    ADJUST_LIGHTING = "ADJUST_LIGHTING"
    REMOVE_OCCLUSIONS = "REMOVE_OCCLUSIONS"
    CAPTURE_CLEAN_REFERENCE = "CAPTURE_CLEAN_REFERENCE"
    RECAPTURE_CLEAN_REFERENCE = "RECAPTURE_CLEAN_REFERENCE"
    RUN_CALIBRATION = "RUN_CALIBRATION"
    ANALYZE_QUALITY = "ANALYZE_QUALITY"
    RESOLVE_QUALITY = "RESOLVE_QUALITY"
    CAPTURE_MEASUREMENT_FRAME = "CAPTURE_MEASUREMENT_FRAME"
    ACCEPT_VIEW = "ACCEPT_VIEW"
    COMPLETE = "COMPLETE"


class PreparationAwareGuidedCaptureReadiness(StrictModel):
    """Read-only composed guidance; preparation remains operator/setup state only."""

    session_id: UUID
    complete: bool
    next_required_view: CaptureViewType | None = None
    next_action: PreparationAwareGuidedAction
    preparation_required: bool
    preparation_policy_version: str
    preparation: CapturePreparationResult | None = None
    guided: GuidedCaptureReadiness


class PreparationAwareGuidedCaptureReadinessService:
    """Fail closed before clean-reference guidance can advance to a capture action."""

    _CAPTURE_ACTIONS = {
        GuidedCaptureAction.CAPTURE_CLEAN_REFERENCE,
        GuidedCaptureAction.RECAPTURE_CLEAN_REFERENCE,
    }

    def __init__(
        self,
        guidance_service: GuidedCaptureReadinessService | None = None,
        preparation_service: CapturePreparationService | None = None,
    ) -> None:
        self._guidance_service = guidance_service or GuidedCaptureReadinessService()
        self._preparation_service = preparation_service or CapturePreparationService()

    def evaluate(
        self,
        session: CaptureSession,
        *,
        observation: CapturePreparationObservation | None = None,
    ) -> PreparationAwareGuidedCaptureReadiness:
        guided = self._guidance_service.evaluate(session)
        guided_action = guided.next_action

        if guided_action not in self._CAPTURE_ACTIONS:
            return self._result(
                guided=guided,
                next_action=PreparationAwareGuidedAction(guided_action.value),
                preparation_required=False,
                preparation=None,
            )

        target_view = guided.next_required_view
        if target_view is None:
            raise GuidedCaptureError(
                "clean-reference guidance requires a next_required_view"
            )

        if observation is None:
            return self._result(
                guided=guided,
                next_action=PreparationAwareGuidedAction.CHECK_PREPARATION,
                preparation_required=True,
                preparation=None,
            )

        if observation.view is not target_view:
            raise GuidedCaptureError(
                "preparation observation view does not match guided capture target: "
                f"expected {target_view.value}, got {observation.view.value}"
            )

        preparation = self._preparation_service.evaluate(observation)
        if not preparation.ready:
            return self._result(
                guided=guided,
                next_action=PreparationAwareGuidedAction(preparation.next_action.value),
                preparation_required=True,
                preparation=preparation,
            )

        return self._result(
            guided=guided,
            next_action=PreparationAwareGuidedAction(guided_action.value),
            preparation_required=True,
            preparation=preparation,
        )

    def _result(
        self,
        *,
        guided: GuidedCaptureReadiness,
        next_action: PreparationAwareGuidedAction,
        preparation_required: bool,
        preparation: CapturePreparationResult | None,
    ) -> PreparationAwareGuidedCaptureReadiness:
        return PreparationAwareGuidedCaptureReadiness(
            session_id=guided.session_id,
            complete=guided.complete,
            next_required_view=guided.next_required_view,
            next_action=next_action,
            preparation_required=preparation_required,
            preparation_policy_version=self._preparation_service.policy.policy_version,
            preparation=preparation,
            guided=guided,
        )
