from __future__ import annotations

from mrea_geometry import (
    Circle,
    ConstraintResolution,
    DimensionBinding,
    GeometryDraft,
    Line,
    Point2D,
    PointEntity,
    ResolvedConstraint,
    StructuralDofAnalyzer,
)


def _constraint(
    constraint_id: str,
    kind: str,
    entity_ids: tuple[str, ...],
) -> ResolvedConstraint:
    return ResolvedConstraint(
        constraint_id=constraint_id,
        kind=kind,
        entity_ids=entity_ids,
        status="INFERRED",
        confidence=1.0,
    )


def _dimension(dimension_id: str, entity_ids: tuple[str, ...]) -> DimensionBinding:
    return DimensionBinding(
        dimension_id=dimension_id,
        measurement_id=f"M-{dimension_id}",
        measurement_type="LINEAR_EXTERNAL",
        value=10.0,
        unit="mm",
        verified=True,
        source="MANUAL_MEASURED",
        target_entity_ids=entity_ids,
        geometry_estimate=10.0,
    )


def _draft(*entities, dimensions=()) -> GeometryDraft:
    return GeometryDraft(
        graph=object(),
        entities=tuple(entities),
        dimensions=tuple(dimensions),
    )


def test_lone_point_is_provably_underconstrained_by_two_dof() -> None:
    draft = _draft(PointEntity("P-1", Point2D(1.0, 2.0)))

    audit = StructuralDofAnalyzer().analyze(
        draft,
        ConstraintResolution(constraints=(), issues=()),
    )

    assert audit.parameter_count == 2
    assert audit.total_equation_upper_bound == 0
    assert audit.remaining_dof_lower_bound == 2
    assert audit.classification == "DEFINITELY_UNDERCONSTRAINED"


def test_line_axis_constraint_and_dimension_still_leave_proven_dof() -> None:
    line = Line("L-1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))
    draft = _draft(line, dimensions=(_dimension("D-LEN", ("L-1",)),))
    resolution = ConstraintResolution(
        constraints=(_constraint("C-H", "HORIZONTAL", ("L-1",)),),
        issues=(),
    )

    audit = StructuralDofAnalyzer().analyze(draft, resolution)

    assert audit.parameter_count == 4
    assert audit.constraint_equation_upper_bound == 1
    assert audit.dimension_equation_upper_bound == 1
    assert audit.total_equation_upper_bound == 2
    assert audit.remaining_dof_lower_bound == 2
    assert audit.classification == "DEFINITELY_UNDERCONSTRAINED"


def test_concentric_equal_circles_use_safe_scalar_equation_upper_bounds() -> None:
    first = Circle("C-1", Point2D(0.0, 0.0), 5.0)
    second = Circle("C-2", Point2D(0.0, 0.0), 5.0)
    resolution = ConstraintResolution(
        constraints=(
            _constraint("K-CON", "CONCENTRIC", ("C-1", "C-2")),
            _constraint("K-EQ", "EQUAL", ("C-1", "C-2")),
        ),
        issues=(),
    )

    audit = StructuralDofAnalyzer().analyze(_draft(first, second), resolution)

    assert audit.parameter_count == 6
    assert audit.constraint_equation_upper_bound == 3
    assert audit.remaining_dof_lower_bound == 3


def test_equation_budget_covering_parameters_does_not_claim_fully_constrained() -> None:
    first = PointEntity("P-1", Point2D(0.0, 0.0))
    second = PointEntity("P-2", Point2D(0.0, 0.0))
    draft = _draft(
        first,
        second,
        dimensions=(
            _dimension("D-1", ("P-1",)),
            _dimension("D-2", ("P-2",)),
        ),
    )
    resolution = ConstraintResolution(
        constraints=(_constraint("C-CO", "COINCIDENT", ("P-1", "P-2")),),
        issues=(),
    )

    audit = StructuralDofAnalyzer().analyze(draft, resolution)

    assert audit.parameter_count == 4
    assert audit.total_equation_upper_bound == 4
    assert audit.remaining_dof_lower_bound == 0
    assert audit.classification == "NOT_PROVEN_UNDERCONSTRAINED"


def test_symmetry_uses_conservative_three_equation_upper_bound() -> None:
    first = Circle("C-1", Point2D(-5.0, 0.0), 2.0)
    second = Circle("C-2", Point2D(5.0, 0.0), 2.0)
    axis = Line("L-AXIS", Point2D(0.0, -10.0), Point2D(0.0, 10.0))
    resolution = ConstraintResolution(
        constraints=(
            _constraint("C-SYM", "SYMMETRIC", ("C-1", "C-2", "L-AXIS")),
        ),
        issues=(),
    )

    audit = StructuralDofAnalyzer().analyze(_draft(first, second, axis), resolution)

    assert audit.parameter_count == 10
    assert audit.constraint_equation_upper_bound == 3
    assert audit.remaining_dof_lower_bound == 7


def test_unknown_constraint_arity_fails_closed_instead_of_claiming_dof_bound() -> None:
    point = PointEntity("P-1", Point2D(0.0, 0.0))
    resolution = ConstraintResolution(
        constraints=(_constraint("C-X", "FUTURE_CONSTRAINT", ("P-1",)),),
        issues=(),
    )

    audit = StructuralDofAnalyzer().analyze(_draft(point), resolution)

    assert audit.remaining_dof_lower_bound is None
    assert audit.classification == "INDETERMINATE_UNKNOWN_CONSTRAINT_ARITY"
    assert audit.unknown_constraint_ids == ("C-X",)


def test_entity_parameter_counts_cover_all_v1_primitive_parameterizations() -> None:
    from mrea_geometry import Arc

    draft = _draft(
        PointEntity("P", Point2D(0.0, 0.0)),
        Line("L", Point2D(0.0, 0.0), Point2D(1.0, 0.0)),
        Circle("C", Point2D(0.0, 0.0), 1.0),
        Arc("A", Point2D(0.0, 0.0), 1.0, 0.0, 90.0),
    )

    audit = StructuralDofAnalyzer().analyze(
        draft,
        ConstraintResolution(constraints=(), issues=()),
    )

    assert audit.entity_parameter_counts == (("A", 5), ("C", 3), ("L", 4), ("P", 2))
    assert audit.parameter_count == 14


def test_audit_is_deterministic_under_entity_constraint_and_dimension_reordering() -> None:
    first = Line("L-1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))
    second = Line("L-2", Point2D(0.0, 5.0), Point2D(10.0, 5.0))
    constraints = (
        _constraint("C-P", "PARALLEL", ("L-1", "L-2")),
        _constraint("C-H1", "HORIZONTAL", ("L-1",)),
    )
    dimensions = (
        _dimension("D-B", ("L-2",)),
        _dimension("D-A", ("L-1",)),
    )
    analyzer = StructuralDofAnalyzer()

    forward = analyzer.analyze(
        _draft(first, second, dimensions=dimensions),
        ConstraintResolution(constraints=constraints, issues=()),
    )
    reverse = analyzer.analyze(
        _draft(second, first, dimensions=tuple(reversed(dimensions))),
        ConstraintResolution(constraints=tuple(reversed(constraints)), issues=()),
    )

    assert forward == reverse
