from __future__ import annotations

import pytest

from mrea_geometry import (
    ConstraintCandidate,
    ConstraintConfidenceModel,
    ConstraintResolver,
    ConstraintSatisfaction,
    ConstraintSatisfactionAnalyzer,
    GeometryDraft,
    Line,
    Point2D,
)


def _satisfaction(*, residual: float, tolerance: float, satisfied: bool = True) -> ConstraintSatisfaction:
    return ConstraintSatisfaction(
        constraint_id="C-1",
        kind="HORIZONTAL",
        entity_ids=("L-1",),
        satisfied=satisfied,
        residual=residual,
        tolerance=tolerance,
        unit="normalized",
    )


def _draft(line: Line) -> GeometryDraft:
    return GeometryDraft(
        graph=object(),
        entities=(line,),
        constraints=(ConstraintCandidate("C-H", "HORIZONTAL", (line.entity_id,)),),
    )


def test_exact_relation_scores_one() -> None:
    score = ConstraintConfidenceModel().score(_satisfaction(residual=0.0, tolerance=0.001))

    assert score.residual_ratio == 0.0
    assert score.confidence == 1.0


def test_half_tolerance_uses_quadratic_confidence_curve() -> None:
    score = ConstraintConfidenceModel().score(_satisfaction(residual=0.0005, tolerance=0.001))

    assert score.residual_ratio == pytest.approx(0.5)
    assert score.confidence == pytest.approx(0.875)


def test_tolerance_boundary_uses_configured_boundary_confidence() -> None:
    score = ConstraintConfidenceModel(boundary_confidence=0.4).score(
        _satisfaction(residual=0.001, tolerance=0.001)
    )

    assert score.residual_ratio == 1.0
    assert score.confidence == pytest.approx(0.4)


def test_unsatisfied_or_nonfinite_relation_scores_zero() -> None:
    unsatisfied = ConstraintConfidenceModel().score(
        _satisfaction(residual=0.002, tolerance=0.001, satisfied=False)
    )
    nonfinite = ConstraintConfidenceModel().score(
        _satisfaction(residual=float("inf"), tolerance=0.001, satisfied=True)
    )

    assert unsatisfied.confidence == 0.0
    assert nonfinite.confidence == 0.0


def test_zero_tolerance_requires_exact_relation() -> None:
    model = ConstraintConfidenceModel()

    exact = model.score(_satisfaction(residual=0.0, tolerance=0.0, satisfied=True))
    nonexact = model.score(_satisfaction(residual=1e-12, tolerance=0.0, satisfied=False))

    assert exact.confidence == 1.0
    assert nonexact.confidence == 0.0


def test_resolver_rejects_satisfied_but_low_quality_relation_by_confidence() -> None:
    line = Line("L-1", Point2D(0.0, 0.0), Point2D(10.0, 0.005))
    resolver = ConstraintResolver(
        minimum_confidence=0.95,
        satisfaction_analyzer=ConstraintSatisfactionAnalyzer(angular_tolerance=0.001),
    )

    resolution = resolver.resolve(_draft(line))

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == ["CONSTRAINT_BELOW_PROMOTION_CONFIDENCE"]


def test_resolver_can_publish_same_relation_when_policy_threshold_is_lower() -> None:
    line = Line("L-1", Point2D(0.0, 0.0), Point2D(10.0, 0.005))
    resolver = ConstraintResolver(
        minimum_confidence=0.85,
        satisfaction_analyzer=ConstraintSatisfactionAnalyzer(angular_tolerance=0.001),
    )

    resolution = resolver.resolve(_draft(line))

    assert resolution.issues == ()
    assert len(resolution.constraints) == 1
    assert resolution.constraints[0].confidence == pytest.approx(0.87500003125, abs=1e-6)


def test_exact_relation_remains_publishable_with_default_policy() -> None:
    line = Line("L-1", Point2D(0.0, 0.0), Point2D(10.0, 0.0))

    resolution = ConstraintResolver().resolve(_draft(line))

    assert resolution.issues == ()
    assert resolution.constraints[0].confidence == 1.0


def test_boundary_confidence_validation() -> None:
    with pytest.raises(ValueError, match="boundary_confidence"):
        ConstraintConfidenceModel(boundary_confidence=1.1)
