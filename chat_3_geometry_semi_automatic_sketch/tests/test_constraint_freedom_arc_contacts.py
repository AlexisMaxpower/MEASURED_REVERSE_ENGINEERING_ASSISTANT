from __future__ import annotations

from dataclasses import replace

from mrea_geometry import (
    Arc,
    Circle,
    ConstraintFreedomAnalyzer,
    ConstraintResolution,
    GeometryPipeline,
    Line,
    Point2D,
    PointEntity,
    ResolvedConstraint,
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


def _draft(*entities):
    return replace(GeometryPipeline().build(tuple(entities), ()), dimensions=())


def test_arc_line_endpoint_coincidence_uses_unique_explicit_witness() -> None:
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 90.0)
    line = Line("L1", Point2D(5.0, 0.0), Point2D(15.0, 0.0))
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(arc, line),
        _resolution(_constraint("C-CO", "COINCIDENT", "A1", "L1")),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_equation_count == 2
    assert diagnosis.supported_rank == 2
    assert diagnosis.degrees_of_freedom == 7
    assert diagnosis.unsupported_constraint_ids == ()


def test_arc_arc_endpoint_coincidence_is_supported_when_witness_is_unique() -> None:
    first = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 90.0)
    second = Arc("A2", Point2D(10.0, 0.0), 5.0, 180.0, 270.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(first, second),
        _resolution(_constraint("C-CO", "COINCIDENT", "A1", "A2")),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_equation_count == 2
    assert diagnosis.supported_rank == 2
    assert diagnosis.unsupported_constraint_ids == ()


def test_arc_coincidence_without_endpoint_topology_witness_fails_closed() -> None:
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 90.0)
    point = PointEntity("P1", Point2D(3.5355339059, 3.5355339059))
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(arc, point),
        _resolution(_constraint("C-CO", "COINCIDENT", "A1", "P1")),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.degrees_of_freedom is None
    assert diagnosis.unsupported_constraint_ids == ("C-CO",)


def test_line_arc_tangent_with_stable_interior_contact_is_supported() -> None:
    line = Line("L1", Point2D(-10.0, 5.0), Point2D(10.0, 5.0))
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 180.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc),
        _resolution(_constraint("C-T", "TANGENT", "L1", "A1")),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_equation_count == 1
    assert diagnosis.supported_rank == 1
    assert diagnosis.unsupported_constraint_ids == ()


def test_line_arc_tangent_outside_trimmed_arc_fails_closed() -> None:
    line = Line("L1", Point2D(-10.0, 5.0), Point2D(10.0, 5.0))
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 180.0, 360.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc),
        _resolution(_constraint("C-T", "TANGENT", "L1", "A1")),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_line_arc_tangent_at_trim_boundary_fails_closed() -> None:
    line = Line("L1", Point2D(-10.0, 5.0), Point2D(10.0, 5.0))
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 90.0, 180.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc),
        _resolution(_constraint("C-T", "TANGENT", "L1", "A1")),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_arc_circle_external_tangent_requires_contact_inside_arc_span() -> None:
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, -45.0, 45.0)
    circle = Circle("C1", Point2D(10.0, 0.0), 5.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(arc, circle),
        _resolution(_constraint("C-T", "TANGENT", "A1", "C1")),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_rank == 1
    assert diagnosis.unsupported_constraint_ids == ()


def test_arc_circle_tangent_outside_arc_span_fails_closed() -> None:
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 45.0, 135.0)
    circle = Circle("C1", Point2D(10.0, 0.0), 5.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(arc, circle),
        _resolution(_constraint("C-T", "TANGENT", "A1", "C1")),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_arc_arc_external_tangent_requires_both_trimmed_spans_to_contain_contact() -> None:
    first = Arc("A1", Point2D(0.0, 0.0), 5.0, -45.0, 45.0)
    second = Arc("A2", Point2D(10.0, 0.0), 5.0, 135.0, 225.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(first, second),
        _resolution(_constraint("C-T", "TANGENT", "A1", "A2")),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_rank == 1
    assert diagnosis.unsupported_constraint_ids == ()


def test_arc_tangent_diagnosis_is_deterministic_for_entity_order() -> None:
    line = Line("L1", Point2D(-10.0, 5.0), Point2D(10.0, 5.0))
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 180.0)
    analyzer = ConstraintFreedomAnalyzer()

    first = analyzer.analyze(
        _draft(line, arc),
        _resolution(_constraint("C-T", "TANGENT", "L1", "A1")),
    )
    second = analyzer.analyze(
        _draft(arc, line),
        _resolution(_constraint("C-T", "TANGENT", "A1", "L1")),
    )

    assert first.to_dict() == second.to_dict()
