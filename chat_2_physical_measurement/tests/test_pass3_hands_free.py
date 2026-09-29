from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest

CHAT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHAT_ROOT / "src"))

from physical_measurement import (  # noqa: E402
    AmbiguousMeasurementCommand,
    CanonicalMeasurementAdapter,
    HandsFreeMeasurementController,
    HandsFreePhase,
    InMemoryMeasurementSessionRepository,
    InvalidMeasurementTransition,
    MeasurementCandidateContext,
    MeasurementCommandError,
    MeasurementCommandIntent,
    MeasurementCommandParser,
    MeasurementSessionService,
    MeasurementType,
    ProvenanceSource,
    normalize_measurement_number,
)


class PrefixSequentialIds:
    def __init__(self) -> None:
        self._values: dict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._values[prefix] += 1
        return f"{prefix}-CHAT2-P3-{self._values[prefix]:03d}"


def build_controller() -> tuple[MeasurementSessionService, str, HandsFreeMeasurementController]:
    fixed = datetime(2026, 9, 29, 18, 30, 0, tzinfo=timezone.utc)
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=PrefixSequentialIds(),
        clock=lambda: fixed,
    )
    session = service.create_session("P-PASS3")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-FRONT-P3",
        reference_frame_id="REF-FRONT-P3",
        x_px=100,
        y_px=200,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-FRONT-P3",
        reference_frame_id="REF-FRONT-P3",
        x_px=522,
        y_px=200,
    )
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            view_id="VIEW-FRONT-P3",
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id="FRAME-FRONT-MEAS-P3",
            uncertainty_mm="0.02",
            instrument_type="DIGITAL_CALIPER",
        ),
    )
    return service, session.session_id, controller


def test_parser_supports_trigger_and_decimal_comma_value() -> None:
    parser = MeasurementCommandParser()

    trigger = parser.parse("  ЗАМЕР  ")
    candidate = parser.parse("замер 42,18")

    assert trigger.intent is MeasurementCommandIntent.TRIGGER
    assert trigger.value is None
    assert candidate.intent is MeasurementCommandIntent.VALUE
    assert candidate.value == Decimal("42.18")


def test_numeric_normalization_is_deterministic_for_dot_comma_and_unit() -> None:
    assert normalize_measurement_number("42,18 мм") == Decimal("42.18")
    assert normalize_measurement_number("42.18 mm") == Decimal("42.18")
    assert normalize_measurement_number("0042,180") == Decimal("42.180")


def test_parser_distinguishes_ambiguous_and_invalid_input() -> None:
    parser = MeasurementCommandParser()

    with pytest.raises(AmbiguousMeasurementCommand):
        parser.parse("замер 42,18 43,20")
    with pytest.raises(AmbiguousMeasurementCommand):
        parser.parse("замер 42,18.5")
    with pytest.raises(MeasurementCommandError):
        parser.parse("замер сорок два")
    with pytest.raises(MeasurementCommandError):
        parser.parse("что-то неизвестное")


def test_voice_candidate_is_unverified_until_explicit_confirmation() -> None:
    service, session_id, controller = build_controller()

    candidate_transition = controller.process_voice_command("замер 42,18")
    candidate = candidate_transition.measurement

    assert candidate is not None
    assert candidate.value == Decimal("42.18")
    assert candidate.source is ProvenanceSource.VOICE_REPORTED
    assert candidate.is_verified is False
    assert candidate.confirmation_source is None
    assert candidate.view_id == "VIEW-FRONT-P3"
    assert candidate.anchor_a.reference_frame_id == "REF-FRONT-P3"
    assert candidate.evidence_frame_id == "FRAME-FRONT-MEAS-P3"
    assert candidate_transition.state.phase is HandsFreePhase.CANDIDATE_PENDING

    verified_transition = controller.process_voice_command("подтвердить")
    verified = verified_transition.measurement

    assert verified is not None
    assert verified.measurement_id == candidate.measurement_id
    assert verified.is_verified is True
    assert verified.source is ProvenanceSource.VOICE_REPORTED
    assert verified.confirmation_source is ProvenanceSource.USER_CONFIRMED
    assert verified_transition.state.phase is HandsFreePhase.VERIFIED
    assert service.get_session(session_id).get(candidate.measurement_id).is_verified is True


def test_trigger_then_ocr_candidate_stays_unverified() -> None:
    service, session_id, controller = build_controller()

    trigger = controller.process_voice_command("замер")
    assert trigger.state.phase is HandsFreePhase.AWAITING_VALUE

    candidate_transition = controller.submit_candidate(
        value="42.18",
        source=ProvenanceSource.OCR_MEASURED,
    )
    candidate = candidate_transition.measurement

    assert candidate is not None
    assert candidate.source is ProvenanceSource.OCR_MEASURED
    assert candidate.is_verified is False
    assert service.get_session(session_id).get(candidate.measurement_id).is_verified is False


def test_device_candidate_requires_same_confirmation_transition() -> None:
    _, _, controller = build_controller()

    candidate = controller.submit_candidate(
        value="42.18",
        source=ProvenanceSource.DEVICE_REPORTED,
    ).measurement
    assert candidate is not None
    assert candidate.source is ProvenanceSource.DEVICE_REPORTED
    assert candidate.is_verified is False

    verified = controller.process_voice_command("подтверждаю").measurement
    assert verified is not None
    assert verified.is_verified is True
    assert verified.confirmation_source is ProvenanceSource.USER_CONFIRMED


def test_reject_removes_unverified_candidate_and_fails_closed_afterward() -> None:
    service, session_id, controller = build_controller()

    candidate = controller.process_voice_command("замер 42,18").measurement
    assert candidate is not None

    rejected = controller.process_voice_command("отклонить")
    assert rejected.state.phase is HandsFreePhase.REJECTED
    assert rejected.state.last_rejected_measurement_id == candidate.measurement_id
    assert service.get_session(session_id).measurements == ()

    with pytest.raises(InvalidMeasurementTransition):
        controller.process_voice_command("подтвердить")


def test_correct_replaces_candidate_without_silent_verification() -> None:
    service, session_id, controller = build_controller()

    first = controller.process_voice_command("замер 42,18").measurement
    assert first is not None

    corrected_transition = controller.process_voice_command("исправить 42,20")
    corrected = corrected_transition.measurement

    assert corrected is not None
    assert corrected.measurement_id != first.measurement_id
    assert corrected.value == Decimal("42.20")
    assert corrected.source is ProvenanceSource.VOICE_REPORTED
    assert corrected.is_verified is False
    assert corrected_transition.state.phase is HandsFreePhase.CANDIDATE_PENDING
    assert corrected_transition.state.last_rejected_measurement_id == first.measurement_id

    session = service.get_session(session_id)
    assert [item.measurement_id for item in session.measurements] == [corrected.measurement_id]


def test_manual_fallback_replaces_reported_candidate_with_manual_provenance() -> None:
    service, session_id, controller = build_controller()

    voice_candidate = controller.process_voice_command("замер 42,18").measurement
    assert voice_candidate is not None

    manual_transition = controller.submit_manual_fallback(value="42.17")
    manual = manual_transition.measurement

    assert manual is not None
    assert manual.measurement_id != voice_candidate.measurement_id
    assert manual.source is ProvenanceSource.MANUAL_MEASURED
    assert manual.is_verified is False
    assert manual.evidence_frame_id == "FRAME-FRONT-MEAS-P3"
    assert manual.anchor_a.reference_frame_id == "REF-FRONT-P3"

    session = service.get_session(session_id)
    assert [item.measurement_id for item in session.measurements] == [manual.measurement_id]


def test_invalid_transitions_are_explicit() -> None:
    _, _, controller = build_controller()

    with pytest.raises(InvalidMeasurementTransition):
        controller.process_voice_command("подтвердить")
    with pytest.raises(InvalidMeasurementTransition):
        controller.process_voice_command("отклонить")
    with pytest.raises(InvalidMeasurementTransition):
        controller.process_voice_command("исправить 42,20")

    controller.process_voice_command("замер")
    with pytest.raises(InvalidMeasurementTransition):
        controller.process_voice_command("замер")

    controller.process_voice_command("замер 42,18")
    with pytest.raises(InvalidMeasurementTransition):
        controller.process_voice_command("замер 42,19")


def test_non_measurement_provenance_cannot_enter_candidate_pipeline() -> None:
    service, session_id, controller = build_controller()

    with pytest.raises(ValueError, match="voice, OCR or device"):
        controller.submit_candidate(
            value="42.18",
            source=ProvenanceSource.AI_INFERRED,
        )

    session = service.get_session(session_id)
    assert session.measurements == ()


def test_verified_voice_candidate_preserves_raw_wire_semantics() -> None:
    service, session_id, controller = build_controller()
    candidate = controller.process_voice_command("замер 42,18").measurement
    assert candidate is not None
    verified = controller.process_voice_command("подтвердить").measurement
    assert verified is not None

    capture_package = {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-PASS3",
        "project_id": "P-PASS3",
        "part_id": "PART-PASS3",
        "views": [
            {
                "view_id": "VIEW-FRONT-P3",
                "clean_reference_frame": {"artifact_id": "REF-FRONT-P3"},
                "measurement_frames": [{"frame_id": "FRAME-FRONT-MEAS-P3"}],
            }
        ],
    }
    ids = PrefixSequentialIds()
    package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=service.get_session(session_id),
        capture_package=capture_package,
    )

    wire = package["measurements"][0]
    assert wire["measurement_id"] == verified.measurement_id
    assert wire["source"] == "VOICE_REPORTED"
    assert wire["verified"] is True
    assert wire["confirmation_source"] == "USER_CONFIRMED"
    assert wire["evidence_frame_id"] == "FRAME-FRONT-MEAS-P3"
    assert {anchor["coordinate_space"] for anchor in wire["anchors"]} == {"IMAGE_PX"}
    assert {anchor["reference_frame_id"] for anchor in wire["anchors"]} == {"REF-FRONT-P3"}
    assert all(anchor["feature_id"] is None for anchor in wire["anchors"])
