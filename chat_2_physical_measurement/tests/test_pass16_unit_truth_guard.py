from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

CHAT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHAT_ROOT / "src"))

from physical_measurement import (  # noqa: E402
    HandsFreeMeasurementController,
    HandsFreePhase,
    InMemoryMeasurementSessionRepository,
    MeasurementCandidateContext,
    MeasurementCommandError,
    MeasurementSessionService,
    MeasurementType,
)


class PrefixSequentialIds:
    def __init__(self) -> None:
        self._values: dict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._values[prefix] += 1
        return f"{prefix}-O1-P16-UNIT-{self._values[prefix]:03d}"


def build_controller(
    measurement_type: MeasurementType,
) -> tuple[MeasurementSessionService, str, HandsFreeMeasurementController]:
    fixed = datetime(2026, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=PrefixSequentialIds(),
        clock=lambda: fixed,
    )
    session = service.create_session("P-O1-PASS16-UNIT")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-O1-P16",
        reference_frame_id="REF-O1-P16",
        x_px=10,
        y_px=20,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-O1-P16",
        reference_frame_id="REF-O1-P16",
        x_px=30,
        y_px=20,
    )
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=measurement_type,
            view_id="VIEW-O1-P16",
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id="FRAME-O1-P16",
        ),
    )
    return service, session.session_id, controller


def test_matching_explicit_linear_unit_is_preserved_as_valid_context() -> None:
    _, _, controller = build_controller(MeasurementType.LINEAR_EXTERNAL)

    transition = controller.process_voice_command("замер 42,18 мм")

    assert transition.measurement is not None
    assert transition.measurement.unit == "mm"
    assert transition.state.phase is HandsFreePhase.CANDIDATE_PENDING


def test_matching_explicit_angle_unit_is_preserved_as_valid_context() -> None:
    _, _, controller = build_controller(MeasurementType.ANGLE)

    transition = controller.process_voice_command("замер 42,18 градусов")

    assert transition.measurement is not None
    assert transition.measurement.unit == "deg"
    assert transition.state.phase is HandsFreePhase.CANDIDATE_PENDING


def test_explicit_degree_unit_cannot_be_relabelled_as_millimetres() -> None:
    service, session_id, controller = build_controller(MeasurementType.LINEAR_EXTERNAL)

    with pytest.raises(MeasurementCommandError, match="explicit unit"):
        controller.process_voice_command("замер 42,18 градусов")

    assert controller.state.phase is HandsFreePhase.IDLE
    assert service.get_session(session_id).measurements == ()


def test_explicit_millimetre_unit_cannot_be_relabelled_as_degrees() -> None:
    service, session_id, controller = build_controller(MeasurementType.ANGLE)

    with pytest.raises(MeasurementCommandError, match="explicit unit"):
        controller.process_voice_command("замер 42,18 мм")

    assert controller.state.phase is HandsFreePhase.IDLE
    assert service.get_session(session_id).measurements == ()


def test_mismatching_correction_is_rejected_before_existing_candidate_mutates() -> None:
    service, session_id, controller = build_controller(MeasurementType.LINEAR_EXTERNAL)
    original = controller.process_voice_command("замер 42,18 мм").measurement
    assert original is not None

    with pytest.raises(MeasurementCommandError, match="explicit unit"):
        controller.process_voice_command("исправить 43,10 градусов")

    state = controller.state
    assert state.phase is HandsFreePhase.CANDIDATE_PENDING
    assert state.current_measurement_id == original.measurement_id
    session = service.get_session(session_id)
    assert [item.measurement_id for item in session.measurements] == [original.measurement_id]
