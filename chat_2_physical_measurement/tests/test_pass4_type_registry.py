from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    CanonicalMeasurementAdapter,
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
    MeasurementTypeRegistry,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS4-{self._value:03d}"


def _capture_package() -> dict[str, object]:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-PASS4",
        "project_id": "P-PASS4",
        "part_id": "PART-PASS4",
        "views": [
            {
                "view_id": "VIEW-FRONT",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "REF-FRONT",
                    "uri": "fixture://pass4/front.png",
                },
                "measurement_frames": [
                    {
                        "frame_id": "EVIDENCE-FRONT-001",
                        "artifact_id": "ART-EVIDENCE-FRONT-001",
                        "uri": "fixture://pass4/evidence.png",
                    }
                ],
            }
        ],
    }


def _service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc),
    )


def test_registry_covers_every_declared_measurement_type() -> None:
    registry = MeasurementTypeRegistry()
    registry.validate_complete()

    assert registry.unit_for(MeasurementType.ANGLE) == "deg"
    for measurement_type in MeasurementType:
        if measurement_type is not MeasurementType.ANGLE:
            assert registry.unit_for(measurement_type) == "mm"


def test_service_assigns_deg_to_angle_and_mm_to_linear_measurement() -> None:
    service = _service()
    session = service.create_session("P-PASS4")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=50,
        y_px=50,
    )

    angle = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="90",
        view_id="VIEW-FRONT",
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id="EVIDENCE-FRONT-001",
    )
    linear = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="42.18",
        view_id="VIEW-FRONT",
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id="EVIDENCE-FRONT-001",
    )

    assert angle.unit == "deg"
    assert linear.unit == "mm"


def test_verified_angle_serializes_with_canonical_deg_unit() -> None:
    service = _service()
    session = service.create_session("P-PASS4")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=50,
        y_px=50,
    )
    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="45.5",
        view_id="VIEW-FRONT",
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id="EVIDENCE-FRONT-001",
    )
    verified = service.confirm_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    package = CanonicalMeasurementAdapter(id_factory=SequentialIds()).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=_capture_package(),
    )

    assert verified.unit == "deg"
    assert package["measurements"][0]["type"] == "ANGLE"
    assert package["measurements"][0]["unit"] == "deg"
    assert package["measurements"][0]["verified"] is True
