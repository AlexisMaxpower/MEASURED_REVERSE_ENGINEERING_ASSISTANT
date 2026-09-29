from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrea_geometry import AnchorRef, Arc, Circle, GeometryPipeline, Line, MeasurementRef, Point2D


def _load_case():
    data = json.loads((ROOT / "tests/fixtures/internal/front_plate_case.json").read_text())
    primitives = []
    for item in data["primitives"]:
        if item["kind"] == "LINE":
            primitives.append(Line(item["entity_id"], Point2D(*item["start"]), Point2D(*item["end"])))
        elif item["kind"] == "CIRCLE":
            primitives.append(Circle(item["entity_id"], Point2D(*item["center"]), item["radius"]))
        elif item["kind"] == "ARC":
            primitives.append(Arc(item["entity_id"], Point2D(*item["center"]), item["radius"], item["start_angle_deg"], item["end_angle_deg"]))
    measurements = []
    for item in data["measurements"]:
        measurements.append(
            MeasurementRef(
                measurement_id=item["measurement_id"],
                measurement_type=item["measurement_type"],
                value=item["value"],
                unit=item["unit"],
                verified=item["verified"],
                source=item["source"],
                anchors=tuple(AnchorRef(a["anchor_id"], Point2D(*a["point"])) for a in item["anchors"]),
            )
        )
    return tuple(primitives), tuple(measurements)


def test_front_case_supports_line_circle_arc_and_graph():
    primitives, measurements = _load_case()
    draft = GeometryPipeline().build(primitives, measurements)
    assert {entity.kind for entity in draft.entities} == {"LINE", "CIRCLE", "ARC"}
    assert draft.graph.adjacency["L1"] == ("L2", "L4")


def test_output_is_deterministic_for_input_order():
    primitives, measurements = _load_case()
    pipeline = GeometryPipeline()
    first = pipeline.build(primitives, measurements).to_dict()
    second = pipeline.build(tuple(reversed(primitives)), tuple(reversed(measurements))).to_dict()
    assert first == second


def test_verified_measurements_keep_value_and_measurement_id():
    primitives, measurements = _load_case()
    draft = GeometryPipeline().build(primitives, measurements)
    width = next(item for item in draft.dimensions if item.measurement_id == "M001")
    assert width.value == 80.2
    assert width.geometry_estimate == pytest.approx(80.2)
    assert width.verified is True
    assert width.target_entity_ids == ("L2", "L4")


def test_candidate_constraints_are_deterministic():
    primitives, measurements = _load_case()
    draft = GeometryPipeline().build(primitives, measurements)
    values = {(item.kind, item.entity_ids) for item in draft.constraints}
    assert ("HORIZONTAL", ("L1",)) in values
    assert ("VERTICAL", ("L2",)) in values
    assert ("EQUAL", ("C1", "C2")) in values


def test_verified_measurement_wins_and_conflict_remains_visible():
    primitives, measurements = _load_case()
    changed = tuple(
        Line("L2", Point2D(79.7, 0.0), Point2D(79.7, 42.1)) if item.entity_id == "L2" else item
        for item in primitives
    )
    remapped = tuple(
        MeasurementRef(
            measurement_id=item.measurement_id,
            measurement_type=item.measurement_type,
            value=item.value,
            unit=item.unit,
            verified=item.verified,
            source=item.source,
            anchors=tuple(
                AnchorRef(anchor.anchor_id, Point2D(79.7, anchor.point.y)) if anchor.anchor_id == "A12" else anchor
                for anchor in item.anchors
            ),
        )
        if item.measurement_id == "M001" else item
        for item in measurements
    )
    draft = GeometryPipeline().build(changed, remapped)
    width = next(item for item in draft.dimensions if item.measurement_id == "M001")
    conflict = next(item for item in draft.conflicts if item.measurement_id == "M001")
    assert width.value == 80.2
    assert width.geometry_estimate == pytest.approx(79.7)
    assert conflict.code == "VERIFIED_MEASUREMENT_VS_DERIVED_GEOMETRY"


def test_unmatched_anchor_is_explicitly_unresolved():
    primitives, measurements = _load_case()
    unresolved_measurement = MeasurementRef(
        measurement_id="M_UNRESOLVED",
        measurement_type="LINEAR_EXTERNAL",
        value=10.0,
        unit="mm",
        verified=True,
        source="MANUAL_MEASURED",
        anchors=(AnchorRef("A_BAD", Point2D(1000.0, 1000.0)),),
    )
    draft = GeometryPipeline().build(primitives, measurements + (unresolved_measurement,))
    unresolved = next(item for item in draft.unresolved if item.measurement_id == "M_UNRESOLVED")
    assert unresolved.code == "ANCHOR_ENTITY_UNRESOLVED_OR_AMBIGUOUS"
    assert all(item.measurement_id != "M_UNRESOLVED" for item in draft.dimensions)
