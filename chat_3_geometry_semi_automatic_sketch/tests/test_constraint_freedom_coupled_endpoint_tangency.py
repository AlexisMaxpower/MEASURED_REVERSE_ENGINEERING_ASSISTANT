from __future__ import annotations

from dataclasses import replace

from mrea_geometry import (
    Arc,
    ConstraintFreedomAnalyzer,
    ConstraintResolution,
    GeometryPipeline,
    Line,
    Point2D,
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


def _line_arc_endpoint_pair() -> tuple[Line, Arc]:
    line = Line("L1", Point2D(5.0, 0.0), Point2D(5.0, 10.0))
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 90.0)
    return line, arc


def _arc_arc_endpoint_pair() -> tuple[Arc, Arc]:
    first = Arc("A1", Point2D(0.0, 0.0), 5.0, -90.0, 0.0)
    second = Arc("A2", Point2D(10.0, 0.0), 5.0, 180.0, 270.0)
    return first, second


def test_line_arc_endpoint_tangent_is_supported_when_same_pair_coincidence_proves_contact() -> None:
    line, arc = _line_arc_endpoint_pair()
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc),
        _resolution(
            _constraint("C-CO", "COINCIDENT", "L1", "A1"),
            _constraint("C-T", "TANGENT", "L1", "A1"),
        ),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_equation_count == 3
    assert diagnosis.supported_rank == 3
    assert diagnosis.unsupported_constraint_ids == ()


def test_line_arc_endpoint_tangent_without_same_pair_coincidence_stays_fail_closed() -> None:
    line, arc = _line_arc_endpoint_pair()
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc),
        _resolution(_constraint("C-T", "TANGENT", "L1", "A1")),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_unrelated_coincidence_does_not_unlock_line_arc_endpoint_tangency() -> None:
    line, arc = _line_arc_endpoint_pair()
    other = Line("L2", Point2D(0.0, 5.0), Point2D(-10.0, 5.0))
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc, other),
        _resolution(
            _constraint("C-OTHER", "COINCIDENT", "A1", "L2"),
            _constraint("C-T", "TANGENT", "L1", "A1"),
        ),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_arc_arc_endpoint_tangent_is_supported_when_same_pair_coincidence_proves_contact() -> None:
    first, second = _arc_arc_endpoint_pair()
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(first, second),
        _resolution(
            _constraint("C-CO", "COINCIDENT", "A1", "A2"),
            _constraint("C-T", "TANGENT", "A1", "A2"),
        ),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_equation_count == 3
    assert diagnosis.supported_rank == 3
    assert diagnosis.unsupported_constraint_ids == ()


def test_arc_arc_endpoint_tangent_without_coincidence_stays_fail_closed() -> None:
    first, second = _arc_arc_endpoint_pair()
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(first, second),
        _resolution(_constraint("C-T", "TANGENT", "A1", "A2")),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_coincidence_does_not_unlock_non_tangent_line_arc_geometry() -> None:
    line = Line("L1", Point2D(5.0, 0.0), Point2D(15.0, 0.0))
    arc = Arc("A1", Point2D(0.0, 0.0), 5.0, 0.0, 90.0)
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(line, arc),
        _resolution(
            _constraint("C-CO", "COINCIDENT", "L1", "A1"),
            _constraint("C-T", "TANGENT", "L1", "A1"),
        ),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.unsupported_constraint_ids == ("C-T",)


def test_coupled_relation_context_does_not_leak_between_analyzer_calls() -> None:
    line, arc = _line_arc_endpoint_pair()
    analyzer = ConstraintFreedomAnalyzer()

    coupled = analyzer.analyze(
        _draft(line, arc),
        _resolution(
            _constraint("C-CO", "COINCIDENT", "L1", "A1"),
            _constraint("C-T", "TANGENT", "L1", "A1"),
        ),
    )
    tangent_only = analyzer.analyze(
        _draft(line, arc),
        _resolution(_constraint("C-T", "TANGENT", "L1", "A1")),
    )

    assert coupled.status == "UNDER_CONSTRAINED"
    assert tangent_only.status == "INDETERMINATE"
    assert tangent_only.unsupported_constraint_ids == ("C-T",)


def test_coupled_endpoint_tangency_is_deterministic_for_entity_and_relation_order() -> None:
    line, arc = _line_arc_endpoint_pair()
    analyzer = ConstraintFreedomAnalyzer()

    first = analyzer.analyze(
        _draft(line, arc),
        _resolution(
            _constraint("C-CO", "COINCIDENT", "L1", "A1"),
            _constraint("C-T", "TANGENT", "L1", "A1"),
        ),
    )
    second = analyzer.analyze(
        _draft(arc, line),
        _resolution(
            _constraint("C-T", "TANGENT", "A1", "L1"),
            _constraint("C-CO", "COINCIDENT", "A1", "L1"),
        ),
    )

    assert first.to_dict() == second.to_dict()
