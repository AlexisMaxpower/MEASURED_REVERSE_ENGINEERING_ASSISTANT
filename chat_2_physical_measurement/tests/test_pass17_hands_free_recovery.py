from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pytest

from physical_measurement import (
    AmbiguousPendingMeasurementRecovery,
    HandsFreeMeasurementController,
    HandsFreePhase,
    HandsFreeRecoveryError,
    MeasurementCandidateContext,
    MeasurementSessionService,
    MeasurementType,
    ProvenanceSource,
    SqliteMeasurementSessionRepository,
    resume_hands_free_controller,
)


class PrefixSequentialIds:
    def __init__(self) -> None:
        self._values: dict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._values[prefix] += 1
        return f"{prefix}-CHAT2-P17-{self._values[prefix]:03d}"


def build_service(database_path: Path) -> MeasurementSessionService:
    return MeasurementSessionService(
        SqliteMeasurementSessionRepository(database_path),
        id_factory=PrefixSequentialIds(),
        clock=lambda: datetime(2026, 10, 2, 1, 0, 0, tzinfo=timezone.utc),
    )


def build_session_and_context(
    database_path: Path,
) -> tuple[MeasurementSessionService, str, MeasurementCandidateContext]:
    service = build_service(database_path)
    session = service.create_session("PROJECT-P17")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-P17",
        reference_frame_id="REF-P17",
        x_px=100,
        y_px=200,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-P17",
        reference_frame_id="REF-P17",
        x_px=522,
        y_px=200,
    )
    context = MeasurementCandidateContext(
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        view_id="VIEW-P17",
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id="FRAME-P17",
        uncertainty="0.02",
        instrument_type="DIGITAL_CALIPER",
    )
    return service, session.session_id, context


def add_voice_candidate(
    service: MeasurementSessionService,
    session_id: str,
    context: MeasurementCandidateContext,
    value: str,
):
    return service.add_reported_candidate(
        session_id=session_id,
        measurement_type=context.measurement_type,
        value=value,
        source=ProvenanceSource.VOICE_REPORTED,
        view_id=context.view_id,
        anchor_a=context.anchor_a,
        anchor_b=context.anchor_b,
        anchor_c=context.anchor_c,
        evidence_frame_id=context.evidence_frame_id,
        uncertainty=context.uncertainty,
        uncertainty_mm=context.uncertainty_mm,
        instrument_type=context.instrument_type,
    )


def test_pending_candidate_survives_sqlite_reopen_and_can_be_confirmed(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    original = add_voice_candidate(service, session_id, context, "42.18")

    reopened = build_service(database_path)
    controller = resume_hands_free_controller(
        service=reopened,
        session_id=session_id,
        context=context,
    )

    assert controller.state.phase is HandsFreePhase.CANDIDATE_PENDING
    assert controller.state.current_measurement_id == original.measurement_id

    verified = controller.process_voice_command("подтвердить").measurement
    assert verified is not None
    assert verified.measurement_id == original.measurement_id
    assert verified.is_verified is True
    assert verified.confirmation_source is ProvenanceSource.USER_CONFIRMED

    second_reopen = build_service(database_path)
    persisted = second_reopen.get_session(session_id).get(original.measurement_id)
    assert persisted.is_verified is True


def test_no_matching_pending_candidate_recovers_as_idle(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    add_voice_candidate(service, session_id, context, "42.18")

    different_context = MeasurementCandidateContext(
        measurement_type=context.measurement_type,
        view_id=context.view_id,
        anchor_a=context.anchor_a,
        anchor_b=context.anchor_b,
        evidence_frame_id="OTHER-FRAME",
        uncertainty=context.uncertainty,
        instrument_type=context.instrument_type,
    )
    controller = resume_hands_free_controller(
        service=build_service(database_path),
        session_id=session_id,
        context=different_context,
    )

    assert controller.state.phase is HandsFreePhase.IDLE
    assert controller.state.current_measurement_id is None


def test_multiple_matching_candidates_fail_closed_without_guessing(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    first = add_voice_candidate(service, session_id, context, "42.18")
    second = add_voice_candidate(service, session_id, context, "42.20")

    reopened = build_service(database_path)
    with pytest.raises(AmbiguousPendingMeasurementRecovery, match="multiple persisted"):
        resume_hands_free_controller(
            service=reopened,
            session_id=session_id,
            context=context,
        )

    assert [item.measurement_id for item in reopened.get_session(session_id).measurements] == [
        first.measurement_id,
        second.measurement_id,
    ]
    assert all(not item.is_verified for item in reopened.get_session(session_id).measurements)


def test_explicit_measurement_id_disambiguates_without_touching_other_candidate(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    first = add_voice_candidate(service, session_id, context, "42.18")
    second = add_voice_candidate(service, session_id, context, "42.20")

    reopened = build_service(database_path)
    controller = resume_hands_free_controller(
        service=reopened,
        session_id=session_id,
        context=context,
        measurement_id=second.measurement_id,
    )
    assert controller.state.current_measurement_id == second.measurement_id

    verified = controller.process_voice_command("подтвердить").measurement
    assert verified is not None
    assert verified.measurement_id == second.measurement_id

    session = reopened.get_session(session_id)
    assert session.get(first.measurement_id).is_verified is False
    assert session.get(second.measurement_id).is_verified is True


def test_verified_candidate_is_not_resumed_as_pending(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    candidate = add_voice_candidate(service, session_id, context, "42.18")
    service.confirm_measurement(
        session_id=session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    reopened = build_service(database_path)
    controller = resume_hands_free_controller(
        service=reopened,
        session_id=session_id,
        context=context,
    )
    assert controller.state.phase is HandsFreePhase.IDLE

    with pytest.raises(HandsFreeRecoveryError, match="already verified"):
        resume_hands_free_controller(
            service=reopened,
            session_id=session_id,
            context=context,
            measurement_id=candidate.measurement_id,
        )


def test_explicit_recovery_rejects_context_mismatch(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    candidate = add_voice_candidate(service, session_id, context, "42.18")
    mismatched = MeasurementCandidateContext(
        measurement_type=context.measurement_type,
        view_id=context.view_id,
        anchor_a=context.anchor_a,
        anchor_b=context.anchor_b,
        evidence_frame_id=context.evidence_frame_id,
        uncertainty="0.03",
        instrument_type=context.instrument_type,
    )

    with pytest.raises(HandsFreeRecoveryError, match="does not match recovery context"):
        resume_hands_free_controller(
            service=build_service(database_path),
            session_id=session_id,
            context=mismatched,
            measurement_id=candidate.measurement_id,
        )


def test_awaiting_value_is_intentionally_not_invented_after_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session_id,
        context=context,
    )
    controller.process_voice_command("замер")
    assert controller.state.phase is HandsFreePhase.AWAITING_VALUE

    recovered = resume_hands_free_controller(
        service=build_service(database_path),
        session_id=session_id,
        context=context,
    )
    assert recovered.state.phase is HandsFreePhase.IDLE


def test_manual_fallback_candidate_can_be_resumed_and_confirmed(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session_id,
        context=context,
    )
    manual = controller.submit_manual_fallback(value="42.17").measurement
    assert manual is not None
    assert manual.source is ProvenanceSource.MANUAL_MEASURED

    recovered = resume_hands_free_controller(
        service=build_service(database_path),
        session_id=session_id,
        context=context,
    )
    assert recovered.state.current_measurement_id == manual.measurement_id
    verified = recovered.process_voice_command("подтвердить").measurement
    assert verified is not None
    assert verified.is_verified is True


def test_recovered_candidate_can_follow_normal_correction_flow(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service, session_id, context = build_session_and_context(database_path)
    original = add_voice_candidate(service, session_id, context, "42.18")

    recovered_service = build_service(database_path)
    controller = resume_hands_free_controller(
        service=recovered_service,
        session_id=session_id,
        context=context,
    )
    corrected = controller.process_voice_command("исправить 42,20").measurement

    assert corrected is not None
    assert corrected.measurement_id != original.measurement_id
    assert str(corrected.value) == "42.20"
    assert corrected.is_verified is False
    session = recovered_service.get_session(session_id)
    assert [item.measurement_id for item in session.measurements] == [corrected.measurement_id]
