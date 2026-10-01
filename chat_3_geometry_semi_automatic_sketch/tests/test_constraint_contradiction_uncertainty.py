from __future__ import annotations

from dataclasses import replace
import math

import pytest

from mrea_geometry import (
    AnchorRef,
    Circle,
    ConstraintCandidate,
    ConstraintResolver,
    DimensionBinding,
    GeometryPipeline,
    MeasurementRef,
    Point2D,
    UncertaintyAwareConstraintResolver,
    UncertaintyAwareGeometryConflictDetector,
    UncertaintyAwareMeasurementContradictionPolicy,
)


def _equal_circle_draft(
    *,
    left_value: float = 10.0,
    right_value: float = 10.2,
    left_uncertainty: float | None = 0.2,
    right_uncertainty: float | None = 0.2,
):
    circles = (
        Circle("C1", Point2D(0.0, 0.0), 5.0, feature_id="HOLE_1"),
        Circle("C2", Point2D(20.0, 0.0), 5.0, feature_id="HOLE_2"),
    )
    measurements = (
        MeasurementRef(
            "M1",
            "DIAMETER_INTERNAL",
            left_value,
            "mm",
            True,
            "MANUAL_MEASURED",
            (AnchorRef("A1", Point2D(5.0, 0.0), feature_id="HOLE_1"),),
            uncertainty=left_uncertainty,
        ),
        MeasurementRef(
            "M2",
            "DIAMETER_INTERNAL",
            right_value,
            "mm",
            True,
            "MANUAL_MEASURED",
            (AnchorRef("A2", Point2D(25.0, 0.0), feature_id="HOLE_2"),),
            uncertainty=right_uncertainty,
        ),
    )
    draft = GeometryPipeline(
        conflict_detector=UncertaintyAwareGeometryConflictDetector()
    ).build(circles, measurements)
    return replace(
        draft,
        constraints=(ConstraintCandidate("C-EQ", "EQUAL", ("C1", "C2"), confidence=1.0),),
    )


def _concentric_draft(*, value: float = 0.2, uncertainty: float | None = 0.2):
    circles = (
        Circle("C1", Point2D(0.0, 0.0), 5.0, feature_id="HOLE_1"),
        Circle("C2", Point2D(0.0, 0.0), 3.0, feature_id="HOLE_2"),
    )
    measurement = MeasurementRef(
        "M-CENTER",
        "CENTER_DISTANCE",
        value,
        "mm",
        True,
        "MANUAL_MEASURED",
        (
            AnchorRef("A1", Point2D(0.0, 0.0), feature_id="HOLE_1"),
            AnchorRef("A2", Point2D(0.0, 0.0), feature_id="HOLE_2"),
        ),
        uncertainty=uncertainty,
    )
    draft = GeometryPipeline(
        conflict_detector=UncertaintyAwareGeometryConflictDetector()
    ).build(circles, (measurement,))
    return replace(
        draft,
        constraints=(
            ConstraintCandidate("C-CON", "CONCENTRIC", ("C1", "C2"), confidence=1.0),
        ),
    )


def _dimension(
    measurement_id: str,
    entity_ids: tuple[str, ...],
    *,
    measurement_type: str,
    value: float,
    uncertainty: float | None,
    unit: str = "mm",
) -> DimensionBinding:
    return DimensionBinding(
        dimension_id=f"D-{measurement_id}",
        measurement_id=measurement_id,
        measurement_type=measurement_type,
        value=value,
        unit=unit,
        verified=True,
        source="MANUAL_MEASURED",
        target_entity_ids=entity_ids,
        geometry_estimate=None,
        uncertainty=uncertainty,
    )


def test_legacy_resolver_keeps_fixed_measurement_contradiction_semantics() -> None:
    draft = _equal_circle_draft()

    legacy = ConstraintResolver().resolve(draft)

    assert legacy.constraints == ()
    assert [item.code for item in legacy.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT"
    ]
    assert legacy.issues[0].measurement_ids == ("M1", "M2")


def test_uncertainty_aware_resolver_allows_equal_when_verified_intervals_overlap() -> None:
    draft = _equal_circle_draft()
    original_dimensions = draft.dimensions

    resolution = UncertaintyAwareConstraintResolver().resolve(draft)

    assert resolution.issues == ()
    assert [item.kind for item in resolution.constraints] == ["EQUAL"]
    assert draft.dimensions == original_dimensions
    assert [item.value for item in draft.dimensions] == [10.0, 10.2]
    assert [item.source for item in draft.dimensions] == ["MANUAL_MEASURED", "MANUAL_MEASURED"]


def test_equal_requires_explicit_uncertainty_on_both_sides_before_relaxing_conflict() -> None:
    draft = _equal_circle_draft(right_uncertainty=None)

    resolution = UncertaintyAwareConstraintResolver().resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT"
    ]


def test_diameter_uncertainty_is_scaled_into_radius_comparison_units() -> None:
    policy = UncertaintyAwareMeasurementContradictionPolicy()
    entities = {
        "C1": Circle("C1", Point2D(0.0, 0.0), 5.0),
        "C2": Circle("C2", Point2D(20.0, 0.0), 5.0),
    }
    candidate = ConstraintCandidate("C-EQ", "EQUAL", ("C1", "C2"))
    dimensions = (
        _dimension(
            "M1", ("C1",), measurement_type="DIAMETER_INTERNAL", value=10.0, uncertainty=0.2
        ),
        _dimension(
            "M2", ("C2",), measurement_type="DIAMETER_INTERNAL", value=10.2, uncertainty=0.2
        ),
    )

    conflict = policy.conflict(
        candidate,
        dimensions=dimensions,
        entities=entities,
        measurement_tolerance=0.05,
    )

    assert conflict is None


def test_equal_still_fails_closed_when_verified_intervals_do_not_overlap() -> None:
    draft = _equal_circle_draft(right_value=12.0)

    resolution = UncertaintyAwareConstraintResolver().resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT"
    ]
    assert resolution.issues[0].measurement_ids == ("M1", "M2")


def test_concentric_uncertainty_can_cover_verified_nonzero_center_distance() -> None:
    draft = _concentric_draft()

    legacy = ConstraintResolver().resolve(draft)
    adjusted = UncertaintyAwareConstraintResolver().resolve(draft)

    assert [item.code for item in legacy.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT"
    ]
    assert adjusted.issues == ()
    assert [item.kind for item in adjusted.constraints] == ["CONCENTRIC"]


def test_concentric_missing_uncertainty_preserves_fixed_conflict_behavior() -> None:
    draft = _concentric_draft(uncertainty=None)

    resolution = UncertaintyAwareConstraintResolver().resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT"
    ]


def test_concentric_still_conflicts_outside_explicit_uncertainty_band() -> None:
    draft = _concentric_draft(value=0.5, uncertainty=0.2)

    resolution = UncertaintyAwareConstraintResolver().resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == [
        "VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT"
    ]
    assert resolution.issues[0].measurement_ids == ("M-CENTER",)


def test_measurement_contradiction_policy_is_deterministic_for_dimension_order() -> None:
    draft = _equal_circle_draft(right_value=12.0)
    resolver = UncertaintyAwareConstraintResolver()

    forward = resolver.resolve(draft)
    reverse = resolver.resolve(replace(draft, dimensions=tuple(reversed(draft.dimensions))))

    assert forward == reverse


@pytest.mark.parametrize("uncertainty", [-0.1, math.inf, -math.inf, math.nan])
def test_invalid_relevant_equal_uncertainty_fails_closed(uncertainty: float) -> None:
    draft = _equal_circle_draft()
    bad_dimensions = (
        _dimension(
            "M1", ("C1",), measurement_type="DIAMETER_INTERNAL", value=10.0, uncertainty=uncertainty
        ),
        _dimension(
            "M2", ("C2",), measurement_type="DIAMETER_INTERNAL", value=10.2, uncertainty=0.2
        ),
    )

    with pytest.raises(ValueError, match="uncertainty"):
        UncertaintyAwareConstraintResolver().resolve(replace(draft, dimensions=bad_dimensions))


def test_relevant_uncertainty_with_non_mm_unit_fails_closed() -> None:
    draft = _equal_circle_draft()
    bad_dimensions = (
        _dimension(
            "M1",
            ("C1",),
            measurement_type="DIAMETER_INTERNAL",
            value=1.0,
            uncertainty=0.02,
            unit="cm",
        ),
        _dimension(
            "M2", ("C2",), measurement_type="DIAMETER_INTERNAL", value=10.2, uncertainty=0.2
        ),
    )

    with pytest.raises(ValueError, match="must use mm"):
        UncertaintyAwareConstraintResolver().resolve(replace(draft, dimensions=bad_dimensions))
