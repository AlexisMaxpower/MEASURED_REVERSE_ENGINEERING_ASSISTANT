from decimal import Decimal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
    ProvenanceSource,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}_{self._value:03d}"


def service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
    )


def test_phase_a_manual_measurement_requires_confirmation_before_verified() -> None:
    svc = service()
    session = svc.create_session("P001")
    a = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF_FRONT", x_px=10, y_px=20
    )
    b = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF_FRONT", x_px=90, y_px=20
    )

    candidate = svc.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="42.18",
        view_id="FRONT",
        anchor_a=a,
        anchor_b=b,
        evidence_frame_id="FRAME_001",
        uncertainty_mm="0.02",
        instrument_type="DIGITAL_CALIPER",
    )

    assert candidate.value == Decimal("42.18")
    assert candidate.source is ProvenanceSource.MANUAL_MEASURED
    assert candidate.confirmed is False
    assert candidate.is_verified is False

    confirmed = svc.confirm_manual_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    assert confirmed.is_verified is True
    assert confirmed.confirmation_source is ProvenanceSource.USER_CONFIRMED
    assert confirmed.confirmed_at is not None


def test_confirmation_cannot_happen_silently() -> None:
    svc = service()
    session = svc.create_session("P001")
    a = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF", x_px=0, y_px=0
    )
    b = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF", x_px=5, y_px=0
    )
    candidate = svc.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.THICKNESS,
        value="3.20",
        view_id="FRONT",
        anchor_a=a,
        anchor_b=b,
    )

    with pytest.raises(ValueError, match="explicit user confirmation"):
        svc.confirm_manual_measurement(
            session_id=session.session_id,
            measurement_id=candidate.measurement_id,
            explicit_user_confirmation=False,
        )


def test_measurement_must_match_anchor_view() -> None:
    svc = service()
    session = svc.create_session("P001")
    a = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF", x_px=0, y_px=0
    )
    b = svc.create_manual_anchor(
        view_id="SIDE", reference_frame_id="REF", x_px=5, y_px=0
    )

    with pytest.raises(ValueError, match="view_id must match"):
        svc.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            value="10",
            view_id="FRONT",
            anchor_a=a,
            anchor_b=b,
        )


def test_measurement_anchors_must_use_same_reference_frame() -> None:
    svc = service()
    session = svc.create_session("P001")
    a = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF_A", x_px=0, y_px=0
    )
    b = svc.create_manual_anchor(
        view_id="FRONT", reference_frame_id="REF_B", x_px=5, y_px=0
    )

    with pytest.raises(ValueError, match="same reference frame"):
        svc.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.CENTER_DISTANCE,
            value="60.00",
            view_id="FRONT",
            anchor_a=a,
            anchor_b=b,
        )


def test_ssot_measurement_type_registry_is_complete() -> None:
    assert {item.value for item in MeasurementType} == {
        "LINEAR_EXTERNAL",
        "LINEAR_INTERNAL",
        "THICKNESS",
        "DEPTH",
        "DIAMETER_EXTERNAL",
        "DIAMETER_INTERNAL",
        "RADIUS",
        "ANGLE",
        "CENTER_DISTANCE",
        "SLOT_WIDTH",
        "SURFACE_DISTANCE",
    }


def test_repository_returns_isolated_session_snapshot() -> None:
    repo = InMemoryMeasurementSessionRepository()
    svc = MeasurementSessionService(repo, id_factory=SequentialIds())
    created = svc.create_session("P001")
    fetched = svc.get_session(created.session_id)

    assert fetched == created
    assert fetched is not created
