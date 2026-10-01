from __future__ import annotations

from decimal import Decimal

from .hands_free import (
    HandsFreeMeasurementController,
    HandsFreeMeasurementState,
    HandsFreePhase,
    MeasurementCandidateContext,
    MeasurementCommandParser,
)
from .models import PhysicalMeasurement, decimal_value
from .service import MeasurementSessionService


class HandsFreeRecoveryError(ValueError):
    """Base class for fail-closed hands-free restart recovery failures."""


class AmbiguousPendingMeasurementRecovery(HandsFreeRecoveryError):
    """More than one persisted candidate matches the controller context."""


def _context_anchors(context: MeasurementCandidateContext) -> tuple:
    return tuple(
        anchor
        for anchor in (context.anchor_a, context.anchor_b, context.anchor_c)
        if anchor is not None
    )


def _context_uncertainty(context: MeasurementCandidateContext) -> Decimal | None:
    neutral = (
        decimal_value(context.uncertainty, "uncertainty")
        if context.uncertainty is not None
        else None
    )
    legacy = (
        decimal_value(context.uncertainty_mm, "uncertainty_mm")
        if context.uncertainty_mm is not None
        else None
    )
    if neutral is not None and legacy is not None and neutral != legacy:
        raise HandsFreeRecoveryError(
            "recovery context uncertainty and uncertainty_mm must match"
        )
    return neutral if neutral is not None else legacy


def _matches_context(
    measurement: PhysicalMeasurement,
    context: MeasurementCandidateContext,
) -> bool:
    return (
        measurement.measurement_type is context.measurement_type
        and measurement.view_id == context.view_id
        and measurement.anchors == _context_anchors(context)
        and measurement.evidence_frame_id == context.evidence_frame_id
        and measurement.instrument_type == context.instrument_type
        and measurement.uncertainty == _context_uncertainty(context)
    )


def _explicit_candidate(
    *,
    service: MeasurementSessionService,
    session_id: str,
    measurement_id: str,
    context: MeasurementCandidateContext,
) -> PhysicalMeasurement:
    normalized_id = measurement_id.strip()
    if not normalized_id:
        raise HandsFreeRecoveryError("measurement_id must not be empty")

    session = service.get_session(session_id)
    try:
        measurement = session.get(normalized_id)
    except KeyError as exc:
        raise HandsFreeRecoveryError(
            f"pending measurement not found in session: {normalized_id}"
        ) from exc

    if measurement.is_verified:
        raise HandsFreeRecoveryError(
            f"measurement is already verified and cannot be resumed: {normalized_id}"
        )
    if not _matches_context(measurement, context):
        raise HandsFreeRecoveryError(
            f"pending measurement does not match recovery context: {normalized_id}"
        )
    return measurement


def _unique_context_candidate(
    *,
    service: MeasurementSessionService,
    session_id: str,
    context: MeasurementCandidateContext,
) -> PhysicalMeasurement | None:
    session = service.get_session(session_id)
    candidates = tuple(
        measurement
        for measurement in session.measurements
        if not measurement.is_verified and _matches_context(measurement, context)
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        ids = ", ".join(measurement.measurement_id for measurement in candidates)
        raise AmbiguousPendingMeasurementRecovery(
            "multiple persisted pending measurements match recovery context; "
            f"select one explicitly: {ids}"
        )
    return candidates[0]


def resume_hands_free_controller(
    *,
    service: MeasurementSessionService,
    session_id: str,
    context: MeasurementCandidateContext,
    parser: MeasurementCommandParser | None = None,
    measurement_id: str | None = None,
) -> HandsFreeMeasurementController:
    """Reconstruct actionable hands-free state from durable session truth.

    Only an unverified physical-measurement candidate can be resumed. If no candidate
    matches the exact measurement context, the controller starts in ``IDLE``. If more
    than one candidate matches, recovery fails closed unless ``measurement_id`` is
    supplied explicitly.

    ``AWAITING_VALUE``, ``VERIFIED`` and ``REJECTED`` are interaction states rather
    than durable facts. They intentionally recover as ``IDLE``; durable verified
    measurements remain present in ``MeasurementSession``.
    """

    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session_id,
        context=context,
        parser=parser,
    )

    candidate = (
        _explicit_candidate(
            service=service,
            session_id=session_id,
            measurement_id=measurement_id,
            context=context,
        )
        if measurement_id is not None
        else _unique_context_candidate(
            service=service,
            session_id=session_id,
            context=context,
        )
    )
    if candidate is None:
        return controller

    controller._state = HandsFreeMeasurementState(
        phase=HandsFreePhase.CANDIDATE_PENDING,
        current_measurement_id=candidate.measurement_id,
    )
    return controller
