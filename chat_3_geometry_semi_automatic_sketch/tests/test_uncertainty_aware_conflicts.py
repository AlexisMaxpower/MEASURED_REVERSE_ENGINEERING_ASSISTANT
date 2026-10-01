from __future__ import annotations

import math

import pytest

from mrea_geometry import (
    AnchorRef,
    GeometryPipeline,
    Line,
    MeasurementRef,
    Point2D,
    UncertaintyAwareGeometryConflictDetector,
)


def _parallel_lines() -> tuple[Line, Line]:
    return (
        Line("L-LEFT", Point2D(0.0, 0.0), Point2D(0.0, 10.0)),
        Line("L-RIGHT", Point2D(9.8, 0.0), Point2D(9.8, 10.0)),
    )


def _measurement(*, uncertainty: float | None, verified: bool = True) -> MeasurementRef:
    return MeasurementRef(
        measurement_id="M-WIDTH",
        measurement_type="LINEAR_EXTERNAL",
        value=10.0,
        unit="mm",
        verified=verified,
        source="MANUAL_MEASURED",
        anchors=(
            AnchorRef("A-LEFT", Point2D(0.0, 5.0)),
            AnchorRef("A-RIGHT", Point2D(9.8, 5.0)),
        ),
        uncertainty=uncertainty,
    )


def _build(
    *,
    uncertainty: float | None,
    tolerance: float = 0.05,
    uncertainty_scale: float = 1.0,
    verified: bool = True,
):
    detector = UncertaintyAwareGeometryConflictDetector(
        tolerance=tolerance,
        uncertainty_scale=uncertainty_scale,
    )
    return GeometryPipeline(conflict_detector=detector).build(
        _parallel_lines(),
        (_measurement(uncertainty=uncertainty, verified=verified),),
    )


def test_missing_uncertainty_preserves_fixed_tolerance_behavior() -> None:
    draft = _build(uncertainty=None)

    assert len(draft.conflicts) == 1
    conflict = draft.conflicts[0]
    assert conflict.delta == pytest.approx(0.2)
    assert conflict.tolerance == pytest.approx(0.05)


def test_explicit_uncertainty_suppresses_false_conflict_inside_band() -> None:
    draft = _build(uncertainty=0.2)

    assert draft.conflicts == ()
    assert len(draft.dimensions) == 1
    dimension = draft.dimensions[0]
    assert dimension.value == pytest.approx(10.0)
    assert dimension.geometry_estimate == pytest.approx(9.8)
    assert dimension.uncertainty == pytest.approx(0.2)
    assert dimension.verified is True
    assert dimension.source == "MANUAL_MEASURED"


def test_conflict_remains_visible_outside_effective_uncertainty_band() -> None:
    draft = _build(uncertainty=0.1)

    assert len(draft.conflicts) == 1
    conflict = draft.conflicts[0]
    assert conflict.measured_value == pytest.approx(10.0)
    assert conflict.derived_value == pytest.approx(9.8)
    assert conflict.delta == pytest.approx(0.2)
    assert conflict.tolerance == pytest.approx(0.15)


def test_uncertainty_scale_is_explicit_and_deterministic() -> None:
    assert _build(uncertainty=0.1, uncertainty_scale=2.0).conflicts == ()

    draft = _build(uncertainty=0.1, uncertainty_scale=0.0)
    assert len(draft.conflicts) == 1
    assert draft.conflicts[0].tolerance == pytest.approx(0.05)


def test_unverified_measurement_is_not_promoted_to_truth_conflict() -> None:
    draft = _build(uncertainty=0.0, verified=False)
    assert draft.conflicts == ()


@pytest.mark.parametrize("uncertainty", [-0.1, math.inf, -math.inf, math.nan])
def test_invalid_uncertainty_fails_closed(uncertainty: float) -> None:
    with pytest.raises(ValueError, match="uncertainty"):
        _build(uncertainty=uncertainty)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tolerance", -0.01),
        ("tolerance", math.inf),
        ("uncertainty_scale", -1.0),
        ("uncertainty_scale", math.nan),
    ],
)
def test_invalid_detector_configuration_fails_closed(field: str, value: float) -> None:
    kwargs = {field: value}
    with pytest.raises(ValueError):
        UncertaintyAwareGeometryConflictDetector(**kwargs)
