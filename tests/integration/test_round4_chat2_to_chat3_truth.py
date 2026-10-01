from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from physical_measurement import (
    CanonicalMeasurementAdapter,
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
)
from mrea_geometry import CanonicalInputAdapter, GeometryPipeline, Point2D, PointEntity


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-R4-X23-{self._value:03d}"


def _capture() -> dict:
    capture = copy.deepcopy(
        json.loads((FIXTURE_ROOT / "capture_package_v1.json").read_text(encoding="utf-8"))
    )
    capture["views"][0]["calibration"]["homography"] = [
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    ]
    return capture


def _anchor(service: MeasurementSessionService, view: dict, x: float, y: float):
    return service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id=view["clean_reference_frame"]["artifact_id"],
        x_px=x,
        y_px=y,
    )


def _confirm(service: MeasurementSessionService, session_id: str, measurement_id: str) -> None:
    service.confirm_measurement(
        session_id=session_id,
        measurement_id=measurement_id,
        explicit_user_confirmation=True,
    )


def test_round4_one_two_three_image_px_anchors_and_mm_deg_units_reach_geometry_unchanged() -> None:
    capture = _capture()
    view = capture["views"][0]
    ids = SequentialIds()
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
    )
    session = service.create_session(capture["project_id"])

    depth_anchor = _anchor(service, view, 5.0, 5.0)
    depth = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.DEPTH,
        value="3.20",
        view_id=view["view_id"],
        anchor_a=depth_anchor,
    )

    line_a = _anchor(service, view, 10.0, 20.0)
    line_b = _anchor(service, view, 50.0, 20.0)
    linear = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="40.00",
        view_id=view["view_id"],
        anchor_a=line_a,
        anchor_b=line_b,
    )

    angle_a = _anchor(service, view, 10.0, 40.0)
    angle_b = _anchor(service, view, 30.0, 60.0)
    angle_c = _anchor(service, view, 50.0, 40.0)
    angle = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="90.0",
        view_id=view["view_id"],
        anchor_a=angle_a,
        anchor_b=angle_b,
        anchor_c=angle_c,
    )

    for measurement in (depth, linear, angle):
        _confirm(service, session.session_id, measurement.measurement_id)

    package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=capture,
    )
    wire_by_type = {item["type"]: item for item in package["measurements"]}

    assert len(wire_by_type["DEPTH"]["anchors"]) == 1
    assert len(wire_by_type["LINEAR_EXTERNAL"]["anchors"]) == 2
    assert len(wire_by_type["ANGLE"]["anchors"]) == 3
    assert wire_by_type["DEPTH"]["unit"] == "mm"
    assert wire_by_type["LINEAR_EXTERNAL"]["unit"] == "mm"
    assert wire_by_type["ANGLE"]["unit"] == "deg"
    assert {
        anchor["coordinate_space"]
        for item in package["measurements"]
        for anchor in item["anchors"]
    } == {"IMAGE_PX"}

    normalized = CanonicalInputAdapter().from_packages(capture, package)
    normalized_by_type = {item.measurement_type: item for item in normalized.measurements}
    assert len(normalized_by_type["DEPTH"].anchors) == 1
    assert len(normalized_by_type["LINEAR_EXTERNAL"].anchors) == 2
    assert len(normalized_by_type["ANGLE"].anchors) == 3
    assert normalized_by_type["DEPTH"].unit == "mm"
    assert normalized_by_type["LINEAR_EXTERNAL"].unit == "mm"
    assert normalized_by_type["ANGLE"].unit == "deg"
    assert {
        anchor.source_coordinate_space
        for item in normalized.measurements
        for anchor in item.anchors
    } == {"IMAGE_PX"}

    entities = (
        PointEntity("P-DEPTH", Point2D(5.0, 5.0), confidence=0.99),
        PointEntity("P-LINE-A", Point2D(10.0, 20.0), confidence=0.99),
        PointEntity("P-LINE-B", Point2D(50.0, 20.0), confidence=0.99),
        PointEntity("P-ANGLE-A", Point2D(10.0, 40.0), confidence=0.99),
        PointEntity("P-ANGLE-B", Point2D(30.0, 60.0), confidence=0.99),
        PointEntity("P-ANGLE-C", Point2D(50.0, 40.0), confidence=0.99),
    )
    draft = GeometryPipeline().build(entities, normalized.measurements)
    assert draft.unresolved == ()
    dimensions = {item.measurement_type: item for item in draft.dimensions}
    assert set(dimensions) == {"DEPTH", "LINEAR_EXTERNAL", "ANGLE"}
    assert dimensions["DEPTH"].unit == "mm"
    assert dimensions["LINEAR_EXTERNAL"].unit == "mm"
    assert dimensions["ANGLE"].unit == "deg"


def test_round4_unit_neutral_uncertainty_is_preserved_through_geometry_binding() -> None:
    capture = _capture()
    view = capture["views"][0]
    ids = SequentialIds()
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
    )
    session = service.create_session(capture["project_id"])

    a = _anchor(service, view, 10.0, 40.0)
    b = _anchor(service, view, 30.0, 60.0)
    c = _anchor(service, view, 50.0, 40.0)
    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="90.0",
        view_id=view["view_id"],
        anchor_a=a,
        anchor_b=b,
        anchor_c=c,
        uncertainty="0.5",
    )
    _confirm(service, session.session_id, candidate.measurement_id)

    package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=capture,
    )
    assert package["measurements"][0]["unit"] == "deg"
    assert package["measurements"][0]["uncertainty"] == pytest.approx(0.5)

    normalized = CanonicalInputAdapter().from_packages(capture, package)
    measurement = normalized.measurements[0]
    assert hasattr(measurement, "uncertainty"), (
        "Chat 3 must preserve canonical measurement uncertainty or explicitly reject it; "
        "silently dropping it is not Round-4 compliant"
    )
    assert measurement.uncertainty == pytest.approx(0.5)

    entities = (
        PointEntity("P-A", Point2D(10.0, 40.0), confidence=0.99),
        PointEntity("P-B", Point2D(30.0, 60.0), confidence=0.99),
        PointEntity("P-C", Point2D(50.0, 40.0), confidence=0.99),
    )
    draft = GeometryPipeline().build(entities, normalized.measurements)
    assert draft.unresolved == ()
    assert len(draft.dimensions) == 1
    dimension = draft.dimensions[0]
    assert hasattr(dimension, "uncertainty"), (
        "Geometry binding must not erase unit-neutral physical uncertainty"
    )
    assert dimension.uncertainty == pytest.approx(0.5)
