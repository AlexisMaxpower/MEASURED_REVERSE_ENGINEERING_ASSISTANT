from __future__ import annotations

from dataclasses import replace

from mrea_geometry import (
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


def _draft(*entities):
    return replace(GeometryPipeline().build(tuple(entities), ()))


def test_line_line_coincident_without_endpoint_witness_fails_closed() -> None:
    first = Line("L1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))
    second = Line("L2", Point2D(20.0, 5.0), Point2D(20.0, 15.0))
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(first, second),
        ConstraintResolution(
            constraints=(_constraint("C-CO", "COINCIDENT", "L1", "L2"),),
            issues=(),
        ),
    )

    assert diagnosis.status == "INDETERMINATE"
    assert diagnosis.degrees_of_freedom is None
    assert diagnosis.unsupported_constraint_ids == ("C-CO",)
    assert [item.code for item in diagnosis.issues] == [
        "CONSTRAINT_FREEDOM_UNSUPPORTED_CONSTRAINT"
    ]


def test_line_line_coincident_with_unique_exact_endpoint_witness_is_supported() -> None:
    first = Line("L1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))
    second = Line("L2", Point2D(10.0, 0.0), Point2D(10.0, 8.0))
    diagnosis = ConstraintFreedomAnalyzer().analyze(
        _draft(first, second),
        ConstraintResolution(
            constraints=(_constraint("C-CO", "COINCIDENT", "L1", "L2"),),
            issues=(),
        ),
    )

    assert diagnosis.status == "UNDER_CONSTRAINED"
    assert diagnosis.supported_equation_count == 2
    assert diagnosis.supported_rank == 2
    assert diagnosis.unsupported_constraint_ids == ()
