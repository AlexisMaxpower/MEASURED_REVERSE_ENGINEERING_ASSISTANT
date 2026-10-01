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
    HandsFreeMeasurementController,
    HandsFreePhase,
    InMemoryMeasurementSessionRepository,
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
        return f"{prefix}-CHAT2-P16-{self._values[prefix]:03d}"


def build_controller() -> tuple[MeasurementSessionService, str, HandsFreeMeasurementController]:
    fixed = datetime(2026, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=PrefixSequentialIds(),
        clock=lambda: fixed,
    )
    session = service.create_session("P-PASS16")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-FRONT-P16",
        reference_frame_id="REF-FRONT-P16",
        x_px=100,
        y_px=200,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-FRONT-P16",
        reference_frame_id="REF-FRONT-P16",
        x_px=522,
        y_px=200,
    )
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            view_id="VIEW-FRONT-P16",
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id="FRAME-FRONT-MEAS-P16",
            uncertainty="0.02",
            instrument_type="DIGITAL_CALIPER",
        ),
    )
    return service, session.session_id, controller


def test_spoken_whole_number_is_deterministic() -> None:
    assert normalize_measurement_number("сорок два") == Decimal("42")
    assert normalize_measurement_number("две тысячи сто сорок два") == Decimal("2142")


def test_compact_caliper_style_spoken_decimal_is_supported() -> None:
    assert normalize_measurement_number("сорок два восемнадцать") == Decimal("42.18")
    assert normalize_measurement_number("сто двадцать три сорок пять") == Decimal("123.45")
    assert normalize_measurement_number("сто один ноль пять") == Decimal("101.05")
    assert normalize_measurement_number("сорок два один восемь") == Decimal("42.18")


def test_explicit_spoken_fraction_preserves_decimal_scale() -> None:
    assert normalize_measurement_number("сорок две целых восемнадцать сотых") == Decimal("42.18")
    assert normalize_measurement_number("ноль целых пять сотых") == Decimal("0.05")
    assert normalize_measurement_number("три целых пять десятых") == Decimal("3.5")
    assert normalize_measurement_number("два целых пять тысячных") == Decimal("2.005")


def test_spoken_sign_and_common_unit_suffixes_are_supported() -> None:
    assert normalize_measurement_number("минус сорок два восемнадцать миллиметра") == Decimal("-42.18")
    assert normalize_measurement_number("плюс сорок два градуса") == Decimal("42")


def test_mixed_or_under_specified_spoken_forms_fail_closed() -> None:
    with pytest.raises(MeasurementCommandError):
        normalize_measurement_number("сорок два пять")
    with pytest.raises(MeasurementCommandError):
        normalize_measurement_number("сорок два 18")
    with pytest.raises(MeasurementCommandError):
        normalize_measurement_number("сорок две целых восемнадцать")
    with pytest.raises(AmbiguousMeasurementCommand):
        normalize_measurement_number("минус -42")


def test_existing_numeric_forms_remain_compatible() -> None:
    assert normalize_measurement_number("42,18 мм") == Decimal("42.18")
    assert normalize_measurement_number("42.18 mm") == Decimal("42.18")
    assert normalize_measurement_number("0042,180") == Decimal("42.180")


def test_voice_parser_emits_spoken_value_candidate() -> None:
    parser = MeasurementCommandParser()
    command = parser.parse("замер сорок два восемнадцать")

    assert command.intent is MeasurementCommandIntent.VALUE
    assert command.value == Decimal("42.18")


def test_spoken_voice_candidate_still_requires_explicit_confirmation() -> None:
    service, session_id, controller = build_controller()

    transition = controller.process_voice_command("замер сорок два восемнадцать")
    candidate = transition.measurement

    assert candidate is not None
    assert candidate.value == Decimal("42.18")
    assert candidate.source is ProvenanceSource.VOICE_REPORTED
    assert candidate.is_verified is False
    assert transition.state.phase is HandsFreePhase.CANDIDATE_PENDING
    assert service.get_session(session_id).get(candidate.measurement_id).is_verified is False

    verified = controller.process_voice_command("подтвердить").measurement
    assert verified is not None
    assert verified.value == Decimal("42.18")
    assert verified.is_verified is True
    assert verified.confirmation_source is ProvenanceSource.USER_CONFIRMED


def test_spoken_correction_replaces_candidate_without_inheriting_verification() -> None:
    service, session_id, controller = build_controller()

    original = controller.process_voice_command("замер сорок два восемнадцать").measurement
    assert original is not None

    transition = controller.process_voice_command("исправить сорок два двадцать")
    corrected = transition.measurement

    assert corrected is not None
    assert corrected.measurement_id != original.measurement_id
    assert corrected.value == Decimal("42.20")
    assert corrected.source is ProvenanceSource.VOICE_REPORTED
    assert corrected.is_verified is False
    assert transition.state.last_rejected_measurement_id == original.measurement_id
    assert [item.measurement_id for item in service.get_session(session_id).measurements] == [
        corrected.measurement_id
    ]


def test_spoken_parser_does_not_turn_invalid_words_into_measurement_truth() -> None:
    _, _, controller = build_controller()

    with pytest.raises(MeasurementCommandError):
        controller.process_voice_command("замер примерно сорок два")
