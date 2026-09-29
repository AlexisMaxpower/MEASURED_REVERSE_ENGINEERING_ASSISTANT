from __future__ import annotations

from dataclasses import replace

from mrea_geometry import (
    Circle,
    ConstraintCandidate,
    ConstraintResolver,
    ConstraintSatisfactionAnalyzer,
    GeometryPipeline,
    Line,
    Point2D,
    PointEntity,
)


def _analyze(candidate: ConstraintCandidate, *entities):
    return ConstraintSatisfactionAnalyzer(
        linear_tolerance=0.05,
        angular_tolerance=1e-3,
    ).analyze(candidate, {item.entity_id: item for item in entities})


def test_axis_residual_distinguishes_satisfied_and_stale_horizontal_relation() -> None:
    good = Line("L-GOOD", Point2D(0.0, 0.0), Point2D(10.0, 0.005))
    bad = Line("L-BAD", Point2D(0.0, 0.0), Point2D(10.0, 0.2))

    good_result = _analyze(ConstraintCandidate("C1", "HORIZONTAL", ("L-GOOD",)), good)
    bad_result = _analyze(ConstraintCandidate("C2", "HORIZONTAL", ("L-BAD",)), bad)

    assert good_result.satisfied is True
    assert bad_result.satisfied is False
    assert good_result.unit == "normalized"


def test_coincident_residual_rejects_pure_interior_crossing() -> None:
    horizontal = Line("L-H", Point2D(-5.0, 0.0), Point2D(5.0, 0.0))
    vertical = Line("L-V", Point2D(0.0, -5.0), Point2D(0.0, 5.0))
    result = _analyze(
        ConstraintCandidate("C-X", "COINCIDENT", ("L-H", "L-V")),
        horizontal,
        vertical,
    )

    assert result.satisfied is False
    assert result.residual > result.tolerance


def test_tangent_residual_detects_stale_line_circle_relation() -> None:
    circle = Circle("C-1", Point2D(0.0, 0.0), 2.0)
    tangent = Line("L-T", Point2D(-4.0, 2.0), Point2D(4.0, 2.0))
    stale = Line("L-S", Point2D(-4.0, 2.25), Point2D(4.0, 2.25))

    good = _analyze(ConstraintCandidate("C-T1", "TANGENT", ("C-1", "L-T")), circle, tangent)
    bad = _analyze(ConstraintCandidate("C-T2", "TANGENT", ("C-1", "L-S")), circle, stale)

    assert good.satisfied is True
    assert good.residual == 0.0
    assert bad.satisfied is False


def test_symmetry_residual_uses_explicit_axis_geometry() -> None:
    axis = Line("L-AX", Point2D(0.0, -10.0), Point2D(0.0, 10.0))
    left = PointEntity("P-L", Point2D(-3.0, 2.0))
    right = PointEntity("P-R", Point2D(3.0, 2.0))
    moved = PointEntity("P-M", Point2D(3.2, 2.0))

    good = _analyze(
        ConstraintCandidate("C-S1", "SYMMETRIC", ("P-L", "P-R", "L-AX")),
        left,
        right,
        axis,
    )
    bad = _analyze(
        ConstraintCandidate("C-S2", "SYMMETRIC", ("P-L", "P-M", "L-AX")),
        left,
        moved,
        axis,
    )

    assert good.satisfied is True
    assert bad.satisfied is False


def test_resolver_turns_stale_candidate_into_explicit_unresolved() -> None:
    line = Line("L-1", Point2D(0.0, 0.0), Point2D(10.0, 0.3))
    draft = GeometryPipeline().build((line,), ())
    stale = ConstraintCandidate("C-H-STALE", "HORIZONTAL", ("L-1",), confidence=1.0)
    draft = replace(draft, constraints=(stale,))

    resolution = ConstraintResolver().resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == ["UNSATISFIED_CONSTRAINT"]
    assert resolution.issues[0].entity_ids == ("L-1",)


def test_existing_generated_candidates_remain_satisfied() -> None:
    rectangle = (
        Line("L-B", Point2D(0.0, 0.0), Point2D(20.0, 0.0)),
        Line("L-R", Point2D(20.0, 0.0), Point2D(20.0, 10.0)),
        Line("L-T", Point2D(20.0, 10.0), Point2D(0.0, 10.0)),
        Line("L-L", Point2D(0.0, 10.0), Point2D(0.0, 0.0)),
    )
    draft = GeometryPipeline().build(rectangle, ())
    resolver = ConstraintResolver()
    resolution = resolver.resolve(draft)

    assert resolution.constraints
    assert not any(item.code == "UNSATISFIED_CONSTRAINT" for item in resolution.issues)
