from __future__ import annotations

import sys
from datetime import datetime, timezone
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
        return f"{prefix}-PASS6-{self._value:03d}"


def _service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 9, 30, 2, 0, tzinfo=timezone.utc),
    )


def _capture_package() -> dict[str, object]:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-PASS6",
        "project_id": "P-PASS6",
        "part_id": "PART-PASS6",
        "views": [
            {
                "view_id": "VIEW-FRONT",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "REF-FRONT",
                    "uri": "fixture://pass6/front.png",
                },
                "measurement_frames": [],
            }
        ],
    }


def _anchor(service: MeasurementSessionService, x: float, y: float, *, view: str = "VIEW-FRONT", ref: str = "REF-FRONT"):
    return service.create_manual_anchor(
        view_id=view,
        reference_frame_id=ref,
        x_px=x,
        y_px=y,
    )


def _wire_for(service: MeasurementSessionService, session_id: str) -> dict[str, object]:
    package = CanonicalMeasurementAdapter(id_factory=SequentialIds()).build_measurement_package(
        session=service.get_session(session_id),
        capture_package=_capture_package(),
    )
    return package["measurements"][0]


def test_single_anchor_candidate_serializes_canonically() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)

    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.DEPTH,
        value="3.20",
        view_id="VIEW-FRONT",
        anchor_a=a,
    )

    assert candidate.anchors == (a,)
    wire = _wire_for(service, session.session_id)
    assert [item["anchor_id"] for item in wire["anchors"]] == [a.anchor_id]
    assert wire["anchors"][0]["coordinate_space"] == "IMAGE_PX"


def test_existing_two_anchor_api_remains_compatible() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)
    b = _anchor(service, 50, 10)

    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="42.18",
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
    )

    assert candidate.anchor_a is a
    assert candidate.anchor_b is b
    assert candidate.anchor_c is None
    assert candidate.anchors == (a, b)


def test_three_anchor_candidate_preserves_order_at_wire_boundary() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)
    b = _anchor(service, 30, 30)
    c = _anchor(service, 50, 10)

    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="45",
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
        anchor_c=c,
    )

    assert candidate.anchors == (a, b, c)
    wire = _wire_for(service, session.session_id)
    assert [item["anchor_id"] for item in wire["anchors"]] == [
        a.anchor_id,
        b.anchor_id,
        c.anchor_id,
    ]


def test_anchor_c_without_anchor_b_fails_closed() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)
    c = _anchor(service, 50, 10)

    with pytest.raises(ValueError, match="anchor_c requires anchor_b"):
        service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.ANGLE,
            value="45",
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_c=c,
        )


def test_duplicate_anchor_ids_fail_closed() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)

    with pytest.raises(ValueError, match="anchors must be unique"):
        service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            value="10",
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=a,
        )


def test_third_anchor_must_match_view_and_reference_frame() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)
    b = _anchor(service, 30, 30)
    wrong_view = _anchor(service, 50, 10, view="SIDE")

    with pytest.raises(ValueError, match="view_id must match"):
        service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.ANGLE,
            value="45",
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            anchor_c=wrong_view,
        )

    wrong_ref = _anchor(service, 50, 10, ref="REF-OTHER")
    with pytest.raises(ValueError, match="same reference frame"):
        service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=MeasurementType.ANGLE,
            value="45",
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            anchor_c=wrong_ref,
        )


def test_hands_free_three_anchor_context_reaches_candidate() -> None:
    service = _service()
    session = service.create_session("P-PASS6")
    a = _anchor(service, 10, 10)
    b = _anchor(service, 30, 30)
    c = _anchor(service, 50, 10)
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=MeasurementType.ANGLE,
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            anchor_c=c,
        ),
    )

    transition = controller.submit_candidate(
        value="45",
        source=ProvenanceSource.VOICE_REPORTED,
    )

    assert transition.measurement is not None
    assert transition.measurement.anchors == (a, b, c)
    assert transition.measurement.is_verified is False
