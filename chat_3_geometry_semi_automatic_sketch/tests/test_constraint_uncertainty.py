from __future__ import annotations

from dataclasses import replace
import math

import pytest

from mrea_geometry import (
    AnchorRef,
    Circle,
    ConstraintCandidate,
    ConstraintResolver,
    ConstraintSatisfactionAnalyzer,
    DimensionBinding,
    GeometryPipeline,
    Line,
    MeasurementRef,
    Point2D,
    UncertaintyAwareConstraintResolver,
    UncertaintyAwareConstraintTolerancePolicy,
    UncertaintyAwareGeometryConflictDetector,
)


def _equal_circle_draft(
    *,
    left_uncertainty: float | None = 0.2,
    right_uncertainty: float | None = 0.2,
):
    circles = (
        Circle("C1", Point2D(0.0, 0.0), 5.0, feature_id="HOLE_1"),
        Circle("C2", Point2D(20.0, 0.0), 5.06, feature_id="HOLE_2"),
    )
    measurements = (
        MeasurementRef(
            "M1",
            "DIAMETER_INTERNAL",
            10.0,
            "mm",
            True,
            "MANUAL_MEASURED",
            (AnchorRef("A1", Point2D(5.0, 0.0), feature_id="HOLE_1"),),
            uncertainty=left_uncertainty,
        ),
        MeasurementRef(
            "M2",
            "DIAMETER_INTERNAL",
            10.0,
            "mm",
            True,
            "MANUAL_MEASURED",
            (AnchorRef("A2", Point2D(25.06, 0.0), feature_id="HOLE_2"),),
            uncertainty=right_uncertainty,
        ),
    )
    draft = GeometryPipeline(
        conflict_detector=UncertaintyAwareGeometryConflictDetector()
    ).build(circles, measurements)
    candidate = ConstraintCandidate("C-EQ", "EQUAL", ("C1", "C2"), confidence=1.0)
    return replace(draft, constraints=(candidate,))


def _concentric_draft(*, uncertainty: float | None = 0.2):
    circles = (
        Circle("C1", Point2D(0.0, 0.0), 5.0, feature_id="HOLE_1"),
        Circle("C2", Point2D(0.06, 0.0), 3.0, feature_id="HOLE_2"),
    )
    measurement = MeasurementRef(
        "M-CENTER",
        "CENTER_DISTANCE",
        0.0,
        "mm",
        True,
        "MANUAL_MEASURED",
        (
            AnchorRef("A1", Point2D(0.0, 0.0), feature_id="HOLE_1"),
            AnchorRef("A2", Point2D(0.06, 0.0), feature_id="HOLE_2"),
        ),
        uncertainty=uncertainty,
    )
    draft = GeometryPipeline(
        conflict_detector=UncertaintyAwareGeometryConflictDetector()
    ).build(circles, (measurement,))
    candidate = ConstraintCandidate("C-CON", "CONCENTRIC", ("C1", "C2"), confidence=1.0)
    return replace(draft, constraints=(candidate,))


def _dimension(
    measurement_id: str,
    entity_ids: tuple[str, ...],
    *,
    measurement_type: str,
    uncertainty: float | None,
    unit: str = "mm",
) -> DimensionBinding:
    return DimensionBinding(
        dimension_id=f"D-{measurement_id}",
        measurement_id=measurement_id,
        measurement_type=measurement_type,
        value=10.0,
        unit=unit,
        verified=True,
        source="MANUAL_MEASURED",
        target_entity_ids=entity_ids,
        geometry_estimate=None,
        uncertainty=uncertainty,
    )


def test_default_resolver_semantics_remain_fixed_tolerance() -> None:
    draft = _equal_circle_draft()

    resolution = ConstraintResolver().resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == ["UNSATISFIED_CONSTRAINT"]


def test_uncertainty_aware_resolver_can_publish_equal_when_residual_is_inside_grounded_band() -> None:
    draft = _equal_circle_draft()
    assert draft.conflicts == ()

    resolution = UncertaintyAwareConstraintResolver().resolve(draft)

    assert resolution.issues == ()
    assert len(resolution.constraints) == 1
    assert resolution.constraints[0].kind == "EQUAL"
    assert resolution.constraints[0].confidence == pytest.approx(0.9712)
    assert [item.value for item in draft.dimensions] == [10.0, 10.0]
    assert [item.source for item in draft.dimensions] == ["MANUAL_MEASURED", "MANUAL_MEASURED"]


def test_diameter_uncertainty_is_converted_to_radius_residual_units() -> None:
    draft = _equal_circle_draft()
    candidate = draft.constraints[0]
    entities = {item.entity_id: item for item in draft.entities}
    baseline = ConstraintSatisfactionAnalyzer().analyze(candidate, entities)

    adjusted = UncertaintyAwareConstraintTolerancePolicy().apply(
        candidate,
        baseline,
        draft.dimensions,
        entities,
    )

    assert baseline.satisfied is False
    assert baseline.tolerance == pytest.approx(0.05)
    assert adjusted.satisfied is True
    assert adjusted.tolerance == pytest.approx(0.25)
    assert adjusted.residual == pytest.approx(0.06)


def test_missing_relevant_uncertainty_preserves_baseline_satisfaction() -> None:
    draft = _equal_circle_draft(right_uncertainty=None)
    candidate = draft.constraints[0]
    entities = {item.entity_id: item for item in draft.entities}
    baseline = ConstraintSatisfactionAnalyzer().analyze(candidate, entities)

    adjusted = UncertaintyAwareConstraintTolerancePolicy().apply(
        candidate,
        baseline,
        draft.dimensions,
        entities,
    )

    assert adjusted == baseline
    resolution = UncertaintyAwareConstraintResolver().resolve(draft)
    assert [item.code for item in resolution.issues] == ["UNSATISFIED_CONSTRAINT"]


def test_center_distance_uncertainty_can_ground_concentric_residual_tolerance() -> None:
    draft = _concentric_draft()

    legacy = ConstraintResolver().resolve(draft)
    adjusted = UncertaintyAwareConstraintResolver().resolve(draft)

    assert [item.code for item in legacy.issues] == ["UNSATISFIED_CONSTRAINT"]
    assert adjusted.issues == ()
    assert len(adjusted.constraints) == 1
    assert adjusted.constraints[0].kind == "CONCENTRIC"
    assert adjusted.constraints[0].confidence == pytest.approx(0.9712)


def test_unrelated_linear_uncertainty_does_not_widen_angular_relation() -> None:
    line = Line("L1", Point2D(0.0, 0.0), Point2D(10.0, 0.02))
    candidate = ConstraintCandidate("C-H", "HORIZONTAL", ("L1",))
    analyzer = ConstraintSatisfactionAnalyzer(angular_tolerance=1e-3)
    baseline = analyzer.analyze(candidate, {"L1": line})
    dimensions = (
        _dimension(
            "M-L",
            ("L1",),
            measurement_type="LINEAR_EXTERNAL",
            uncertainty=100.0,
        ),
    )

    adjusted = UncertaintyAwareConstraintTolerancePolicy().apply(
        candidate,
        baseline,
        dimensions,
        {"L1": line},
    )

    assert adjusted == baseline
    assert adjusted.unit == "normalized"
    assert adjusted.satisfied is False


def test_smallest_explicit_precision_is_selected_deterministically() -> None:
    entities = {
        "C1": Circle("C1", Point2D(0.0, 0.0), 5.0),
        "C2": Circle("C2", Point2D(20.0, 0.0), 5.06),
    }
    candidate = ConstraintCandidate("C-EQ", "EQUAL", ("C1", "C2"))
    baseline = ConstraintSatisfactionAnalyzer().analyze(candidate, entities)
    dimensions = (
        _dimension("M1-WIDE", ("C1",), measurement_type="DIAMETER_INTERNAL", uncertainty=0.4),
        _dimension("M1-TIGHT", ("C1",), measurement_type="DIAMETER_INTERNAL", uncertainty=0.2),
        _dimension("M2", ("C2",), measurement_type="DIAMETER_INTERNAL", uncertainty=0.2),
    )
    policy = UncertaintyAwareConstraintTolerancePolicy()

    forward = policy.apply(candidate, baseline, dimensions, entities)
    reverse = policy.apply(candidate, baseline, tuple(reversed(dimensions)), entities)

    assert forward == reverse
    assert forward.tolerance == pytest.approx(0.25)


@pytest.mark.parametrize("uncertainty", [-0.1, math.inf, -math.inf, math.nan])
def test_invalid_relevant_uncertainty_fails_closed(uncertainty: float) -> None:
    entities = {
        "C1": Circle("C1", Point2D(0.0, 0.0), 5.0),
        "C2": Circle("C2", Point2D(20.0, 0.0), 5.06),
    }
    candidate = ConstraintCandidate("C-EQ", "EQUAL", ("C1", "C2"))
    baseline = ConstraintSatisfactionAnalyzer().analyze(candidate, entities)
    dimensions = (
        _dimension("M1", ("C1",), measurement_type="DIAMETER_INTERNAL", uncertainty=uncertainty),
        _dimension("M2", ("C2",), measurement_type="DIAMETER_INTERNAL", uncertainty=0.2),
    )

    with pytest.raises(ValueError, match="uncertainty"):
        UncertaintyAwareConstraintTolerancePolicy().apply(
            candidate,
            baseline,
            dimensions,
            entities,
        )


@pytest.mark.parametrize("scale", [-1.0, math.inf, math.nan])
def test_invalid_uncertainty_scale_fails_closed(scale: float) -> None:
    with pytest.raises(ValueError, match="uncertainty_scale"):
        UncertaintyAwareConstraintTolerancePolicy(uncertainty_scale=scale)
