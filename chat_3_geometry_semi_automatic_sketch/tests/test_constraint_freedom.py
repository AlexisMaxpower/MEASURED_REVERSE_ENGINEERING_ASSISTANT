from __future__ import annotations

from dataclasses import replace

from mrea_geometry import (
    Arc,
    Circle,
    ConstraintFreedomAnalyzer,
    ConstraintResolution,
    DimensionBinding,
    GeometryConflict,
    GeometryPipeline,
    Line,
    Point2D,
    PointEntity,
    ResolvedConstraint,
    UnresolvedBinding,
)


def _constraint(constraint_id: str, kind: str, *entity_ids: str) -> ResolvedConstraint:
    return ResolvedConstraint(
        constraint_id=constraint_id,
        kind=kind,
        entity_ids=tuple(entity_ids),
        status="INFERRED",
        confidence=1.0,
    )


def _resolution(*constraints: ResolvedConstraint) -> ConstraintResolution:
    return ConstraintResolution(constraints=tuple(constraints), issues=())


def _dimension(
    dimension_id: str,
    measurement_type: str,
    value: float,
    *entity_ids: str,
    unit: str = "mm",
    verified: bool = True,
) -> DimensionBinding:
    return DimensionBinding(
        dimension_id=dimension_id,
        measurement_id=f"M-{dimension_id}",
        measurement_type=measurement_type,
        value=value,
        unit=unit,
        verified=verified,
        source="MANUAL_MEASURED",
        target_entity_ids=tuple(entity_ids),
        geometry_estimate=value,
        uncertainty=0.02 if verified else None,
    )


def _draft(*entities, dimensions=(), unresolved=(), conflicts=()):
    base = GeometryPipeline().build(tuple(entities), ())
    return replace(
        base,
        dimensions=tuple(dimensions),
        unresolved=tuple(unresolved),
        conflicts=tuple(conflicts),
    )


def test_free_line_reports_one_internal_shape_dof_plus_rigid_frame() -> None:
    draft = _draft(Line("L1", Point2D(0.0, 0.0), Point2D(10.0, 0.0)))

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.variable_count == 4
    assert diagnosis.supported_rank == 0
    assert diagnosis.degrees_of_freedom == 4
    assert diagnosis.frame_degrees_of_freedom == 3
    assert diagnosis.internal_degrees_of_freedom == 1
    assert not diagnosis.fully_constrained


def test_coincident_points_are_constrained_up_to_translation_frame() -> None:
    draft = _draft(
        PointEntity("P1", Point2D(2.0, 3.0)),
        PointEntity("P2", Point2D(2.0, 3.0)),
    )
    resolution = _resolution(_constraint("C-CO", "COINCIDENT", "P1", "P2"))

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONSTRAINED_UP_TO_FRAME"
    assert diagnosis.variable_count == 4
    assert diagnosis.supported_equation_count == 2
    assert diagnosis.supported_rank == 2
    assert diagnosis.degrees_of_freedom == 2
    assert diagnosis.frame_degrees_of_freedom == 2
    assert diagnosis.internal_degrees_of_freedom == 0
    assert diagnosis.constrained_up_to_frame


def test_verified_circle_radius_removes_shape_dof_but_preserves_center_frame() -> None:
    circle = Circle("C1", Point2D(4.0, 7.0), 5.0)
    draft = _draft(circle, dimensions=(_dimension("D-R", "RADIUS", 5.0, "C1"),))

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "CONSTRAINED_UP_TO_FRAME"
    assert diagnosis.variable_count == 3
    assert diagnosis.supported_rank == 1
    assert diagnosis.degrees_of_freedom == 2
    assert diagnosis.frame_degrees_of_freedom == 2
    assert diagnosis.internal_degrees_of_freedom == 0


def test_arc_radius_still_leaves_arc_span_shape_freedom() -> None:
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 90.0)
    draft = _draft(arc, dimensions=(_dimension("D-R", "RADIUS", 5.0, "A1"),))

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.variable_count == 5
    assert diagnosis.supported_rank == 1
    assert diagnosis.degrees_of_freedom == 4
    assert diagnosis.frame_degrees_of_freedom == 3
    assert diagnosis.internal_degrees_of_freedom == 1


def test_rectangle_profile_is_constrained_up_to_xy_frame() -> None:
    bottom = Line("L-B", Point2D(0.0, 0.0), Point2D(80.0, 0.0))
    right = Line("L-R", Point2D(80.0, 0.0), Point2D(80.0, 40.0))
    top = Line("L-T", Point2D(80.0, 40.0), Point2D(0.0, 40.0))
    left = Line("L-L", Point2D(0.0, 40.0), Point2D(0.0, 0.0))
    draft = _draft(
        bottom,
        right,
        top,
        left,
        dimensions=(
            _dimension("D-W", "LINEAR_EXTERNAL", 80.0, "L-L", "L-R"),
            _dimension("D-H", "LINEAR_EXTERNAL", 40.0, "L-B", "L-T"),
        ),
    )
    resolution = _resolution(
        _constraint("C-HB", "HORIZONTAL", "L-B"),
        _constraint("C-HY", "HORIZONTAL", "L-T"),
        _constraint("C-VL", "VERTICAL", "L-L"),
        _constraint("C-VR", "VERTICAL", "L-R"),
        _constraint("C-BR", "COINCIDENT", "L-B", "L-R"),
        _constraint("C-RT", "COINCIDENT", "L-R", "L-T"),
        _constraint("C-TL", "COINCIDENT", "L-T", "L-L"),
        _constraint("C-LB", "COINCIDENT", "L-L", "L-B"),
    )

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONSTRAINED_UP_TO_FRAME"
    assert diagnosis.variable_count == 16
    assert diagnosis.degrees_of_freedom == 2
    assert diagnosis.frame_degrees_of_freedom == 2
    assert diagnosis.internal_degrees_of_freedom == 0
    assert diagnosis.unsupported_constraint_ids == ()
    assert diagnosis.unsupported_dimension_ids == ()


def test_verified_angle_dimension_fails_closed_as_indeterminate() -> None:
    first = Line("L1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))
    second = Line("L2", Point2D(0.0, 0.0), Point2D(0.0, 10.0))
    draft = _draft(
        first,
        second,
        dimensions=(_dimension("D-A", "ANGLE", 90.0, "L1", "L2", unit="deg"),),
    )

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.degrees_of_freedom is None
    assert diagnosis.unsupported_dimension_ids == ("D-A",)
    assert [item.code for item in diagnosis.issues] == [
        "CONSTRAINT_FREEDOM_UNSUPPORTED_VERIFIED_DIMENSION"
    ]


def test_unverified_unsupported_dimension_does_not_constrain_or_block_dof() -> None:
    point = PointEntity("P1", Point2D(1.0, 2.0))
    draft = _draft(
        point,
        dimensions=(_dimension("D-A", "ANGLE", 45.0, "P1", unit="deg", verified=False),),
    )

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "CONSTRAINED_UP_TO_FRAME"
    assert diagnosis.degrees_of_freedom == 2
    assert diagnosis.frame_degrees_of_freedom == 2
    assert diagnosis.internal_degrees_of_freedom == 0
    assert diagnosis.unsupported_dimension_ids == ()


def test_unresolved_measurement_binding_blocks_exact_dof_claim() -> None:
    draft = _draft(
        PointEntity("P1", Point2D(1.0, 2.0)),
        unresolved=(UnresolvedBinding("M-X", "ANCHOR_ENTITY_UNRESOLVED_OR_AMBIGUOUS", ("A1",)),),
    )

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.degrees_of_freedom is None
    assert [item.code for item in diagnosis.issues] == [
        "CONSTRAINT_FREEDOM_UNRESOLVED_MEASUREMENT_BINDING"
    ]


def test_verified_geometry_conflict_blocks_dof_claim() -> None:
    draft = _draft(
        Circle("C1", Point2D(0.0, 0.0), 5.0),
        conflicts=(
            GeometryConflict(
                conflict_id="GC-M1",
                code="VERIFIED_MEASUREMENT_VS_DERIVED_GEOMETRY",
                measurement_id="M1",
                measured_value=12.0,
                derived_value=10.0,
                delta=2.0,
                tolerance=0.05,
            ),
        ),
    )

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, _resolution())

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.degrees_of_freedom is None
    assert [item.code for item in diagnosis.issues] == [
        "CONSTRAINT_FREEDOM_PHYSICAL_MEASUREMENT_CONFLICT"
    ]


def test_global_constraint_conflict_blocks_dof_claim() -> None:
    line = Line("L1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))
    draft = _draft(line)
    resolution = _resolution(
        _constraint("C-H", "HORIZONTAL", "L1"),
        _constraint("C-V", "VERTICAL", "L1"),
    )

    diagnosis = ConstraintFreedomAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.degrees_of_freedom is None
    assert diagnosis.issues[0].constraint_ids == ("C-H", "C-V")


def test_diagnosis_is_deterministic_for_entity_and_constraint_order() -> None:
    p1 = PointEntity("P1", Point2D(2.0, 3.0))
    p2 = PointEntity("P2", Point2D(2.0, 3.0))
    first = ConstraintFreedomAnalyzer().analyze(
        _draft(p1, p2),
        _resolution(_constraint("C-CO", "COINCIDENT", "P1", "P2")),
    )
    second = ConstraintFreedomAnalyzer().analyze(
        _draft(p2, p1),
        _resolution(_constraint("C-CO", "COINCIDENT", "P2", "P1")),
    )

    assert first.to_dict() == second.to_dict()
