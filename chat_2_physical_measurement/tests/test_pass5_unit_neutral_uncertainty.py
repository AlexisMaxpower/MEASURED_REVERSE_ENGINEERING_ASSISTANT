from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    CanonicalMeasurementAdapter,
    HandsFreeMeasurementController,
    InMemoryMeasurementSessionRepository,
    MeasurementCandidateContext,
    MeasurementSessionService,
    MeasurementType,
    ProvenanceSource,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS5-{self._value:03d}"


def _service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 9, 30, 1, 0, tzinfo=timezone.utc),
    )


def _anchors(service: MeasurementSessionService):
    a = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    b = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=50,
        y_px=50,
    )
    return a, b


def _capture_package() -> dict[str, object]:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-PASS5",
        "project_id": "P-PASS5",
        "part_id": "PART-PASS5",
        "views": [
            {
                "view_id": "VIEW-FRONT",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "REF-FRONT",
                    "uri": "fixture://pass5/front.png",
                },
                "measurement_frames": [
                    {
                        "frame_id": "EVIDENCE-FRONT-001",
                        "artifact_id": "ART-EVIDENCE-FRONT-001",
                        "uri": "fixture://pass5/evidence.png",
                    }
                ],
            }
        ],
    }


def test_angle_uncertainty_uses_measurement_unit_and_serializes_canonically() -> None:
    service = _service()
    session = service.create_session("P-PASS5")
    a, b = _anchors(service)

    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="45.5",
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
        evidence_frame_id="EVIDENCE-FRONT-001",
        uncertainty="0.5",
    )
    service.confirm_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    package = CanonicalMeasurementAdapter(id_factory=SequentialIds()).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=_capture_package(),
    )
    wire = package["measurements"][0]

    assert candidate.unit == "deg"
    assert candidate.uncertainty == Decimal("0.5")
    assert candidate.uncertainty_mm is None
    assert wire["unit"] == "deg"
    assert wire["uncertainty"] == 0.5


def test_legacy_uncertainty_mm_remains_compatible_for_mm_measurements() -> None:
    service = _service()
    session = service.create_session("P-PASS5")
    a, b = _anchors(service)

    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="42.18",
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
        uncertainty_mm="0.02",
    )

    assert candidate.unit == "mm"
    assert candidate.uncertainty == Decimal("0.02")
    assert candidate.uncertainty_mm == Decimal("0.02")


def test_legacy_uncertainty_mm_fails_closed_for_angle() -> None:
    service = _service()
    session = service.create_session("P-PASS5")
    a, b = _anchors(service)

    with pytest.raises(ValueError, match="only valid for mm measurements"):
        service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.ANGLE,
            value="90",
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            uncertainty_mm="0.5",
        )


def test_conflicting_new_and_legacy_uncertainty_fails_closed() -> None:
    service = _service()
    session = service.create_session("P-PASS5")
    a, b = _anchors(service)

    with pytest.raises(ValueError, match="must match"):
        service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            value="42.18",
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            uncertainty="0.03",
            uncertainty_mm="0.02",
        )


def test_hands_free_context_propagates_unit_neutral_angle_uncertainty() -> None:
    service = _service()
    session = service.create_session("P-PASS5")
    a, b = _anchors(service)
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=MeasurementType.ANGLE,
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            evidence_frame_id="EVIDENCE-FRONT-001",
            uncertainty="0.25",
        ),
    )

    transition = controller.submit_candidate(
        value="30",
        source=ProvenanceSource.VOICE_REPORTED,
    )

    assert transition.measurement is not None
    assert transition.measurement.unit == "deg"
    assert transition.measurement.uncertainty == Decimal("0.25")
    assert transition.measurement.uncertainty_mm is None
