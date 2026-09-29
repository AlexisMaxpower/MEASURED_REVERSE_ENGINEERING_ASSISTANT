from __future__ import annotations

from mrea_geometry import (
    AnchorRef,
    CanonicalGeometryInput,
    Circle,
    ConstraintResolver,
    GeometryPipeline,
    Line,
    MeasurementRef,
    Point2D,
    SketchPackageBuilder,
)


def _rectangle() -> tuple[Line, ...]:
    return (
        Line("L-BOTTOM", Point2D(0, 0), Point2D(40, 0)),
        Line("L-RIGHT", Point2D(40, 0), Point2D(40, 20)),
        Line("L-TOP", Point2D(40, 20), Point2D(0, 20)),
        Line("L-LEFT", Point2D(0, 20), Point2D(0, 0)),
    )


def _context() -> CanonicalGeometryInput:
    return CanonicalGeometryInput(
        project_id="P-C4",
        part_id="PART-C4",
        capture_package_id="CP-C4",
        measurement_package_id="MP-C4",
        view_id="VIEW-C4",
        source_view_ids=("VIEW-C4",),
        coordinate_system="MAT_XY_MM",
        measurements=(),
    )


def test_axis_constraints_promote_and_redundant_pair_constraints_drop() -> None:
    draft = GeometryPipeline().build(_rectangle(), ())
    resolution = ConstraintResolver().resolve(draft)

    assert [item.constraint_id for item in resolution.constraints] == [
        "C_COINCIDENT_L-BOTTOM_L-LEFT",
        "C_COINCIDENT_L-BOTTOM_L-RIGHT",
        "C_COINCIDENT_L-LEFT_L-TOP",
        "C_COINCIDENT_L-RIGHT_L-TOP",
        "C_EQUAL_L-BOTTOM_L-TOP",
        "C_EQUAL_L-LEFT_L-RIGHT",
        "C_HORIZONTAL_L-BOTTOM",
        "C_HORIZONTAL_L-TOP",
        "C_VERTICAL_L-LEFT",
        "C_VERTICAL_L-RIGHT",
    ]
    assert resolution.issues == ()
    assert {item.status for item in resolution.constraints} == {"INFERRED"}
    assert not any(item.kind in {"PARALLEL", "PERPENDICULAR"} for item in resolution.constraints)


def test_rotated_geometry_keeps_nonredundant_parallel_and_perpendicular_relations() -> None:
    square = (
        Line("L1", Point2D(0, 1), Point2D(1, 2)),
        Line("L2", Point2D(1, 2), Point2D(2, 1)),
        Line("L3", Point2D(2, 1), Point2D(1, 0)),
        Line("L4", Point2D(1, 0), Point2D(0, 1)),
    )
    draft = GeometryPipeline().build(square, ())
    resolution = ConstraintResolver().resolve(draft)

    kinds = {item.kind for item in resolution.constraints}
    assert "PARALLEL" in kinds
    assert "PERPENDICULAR" in kinds
    assert not {"HORIZONTAL", "VERTICAL"} & kinds


def test_equal_circle_constraint_is_suppressed_by_verified_diameter_conflict() -> None:
    circles = (
        Circle("C1", Point2D(0, 0), 5.0, feature_id="HOLE_1"),
        Circle("C2", Point2D(20, 0), 5.0, feature_id="HOLE_2"),
    )
    measurements = (
        MeasurementRef(
            "M1", "DIAMETER_INTERNAL", 10.0, "mm", True, "MANUAL_MEASURED",
            (AnchorRef("A1", Point2D(5, 0), feature_id="HOLE_1"),),
        ),
        MeasurementRef(
            "M2", "DIAMETER_INTERNAL", 12.0, "mm", True, "MANUAL_MEASURED",
            (AnchorRef("A2", Point2D(25, 0), feature_id="HOLE_2"),),
        ),
    )
    draft = GeometryPipeline().build(circles, measurements)
    resolution = ConstraintResolver().resolve(draft)

    assert not any(item.kind == "EQUAL" for item in resolution.constraints)
    assert [item.code for item in resolution.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT"
    ]
    assert resolution.issues[0].measurement_ids == ("M1", "M2")


def test_concentric_constraint_is_suppressed_by_verified_center_distance() -> None:
    circles = (
        Circle("C1", Point2D(0, 0), 5.0, feature_id="HOLE_1"),
        Circle("C2", Point2D(0, 0), 3.0, feature_id="HOLE_2"),
    )
    measurement = MeasurementRef(
        "M-CENTER", "CENTER_DISTANCE", 4.0, "mm", True, "MANUAL_MEASURED",
        (
            AnchorRef("A1", Point2D(0, 0), feature_id="HOLE_1"),
            AnchorRef("A2", Point2D(0, 0), feature_id="HOLE_2"),
        ),
    )
    draft = GeometryPipeline().build(circles, (measurement,))
    resolution = ConstraintResolver().resolve(draft)

    assert not any(item.kind == "CONCENTRIC" for item in resolution.constraints)
    assert [item.code for item in resolution.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT"
    ]
    assert resolution.issues[0].measurement_ids == ("M-CENTER",)


def test_resolution_is_deterministic_for_reversed_primitive_order() -> None:
    forward = GeometryPipeline().build(_rectangle(), ())
    reverse = GeometryPipeline().build(tuple(reversed(_rectangle())), ())
    resolver = ConstraintResolver()
    assert resolver.resolve(forward) == resolver.resolve(reverse)


def test_builder_publishes_resolved_constraints_only_when_explicitly_supplied() -> None:
    draft = GeometryPipeline().build(_rectangle(), ())
    resolution = ConstraintResolver().resolve(draft)

    legacy = SketchPackageBuilder().build(draft, _context(), sketch_package_id="SP-LEGACY")
    promoted = SketchPackageBuilder().build(
        draft,
        _context(),
        sketch_package_id="SP-PROMOTED",
        constraint_resolution=resolution,
    )

    assert legacy["constraints"] == []
    assert promoted["constraints"] == [item.to_canonical() for item in resolution.constraints]
    assert all(
        set(item) == {"constraint_id", "type", "entity_ids", "status"}
        for item in promoted["constraints"]
    )


def test_entity_confidence_limits_constraint_promotion() -> None:
    circles = (
        Circle("C1", Point2D(0, 0), 5.0, confidence=0.80),
        Circle("C2", Point2D(20, 0), 5.0, confidence=0.82),
    )
    draft = GeometryPipeline().build(circles, ())
    resolution = ConstraintResolver(minimum_confidence=0.95).resolve(draft)

    assert not any(item.kind == "EQUAL" for item in resolution.constraints)
    assert [item.code for item in resolution.issues] == [
        "CONSTRAINT_BELOW_PROMOTION_CONFIDENCE"
    ]
