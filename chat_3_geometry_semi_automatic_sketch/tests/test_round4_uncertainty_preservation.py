from __future__ import annotations

import copy

import pytest

from mrea_geometry import CanonicalInputAdapter, GeometryPipeline, Point2D, PointEntity


def _capture() -> dict:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-R4-UNCERTAINTY-001",
        "project_id": "P-R4-UNCERTAINTY-001",
        "part_id": "PART-R4-UNCERTAINTY-001",
        "views": [
            {
                "view_id": "VIEW-FRONT-001",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "A-FRONT-CLEAN-001",
                    "kind": "CLEAN_REFERENCE_IMAGE",
                    "uri": "fixture://front.png",
                    "media_type": "image/png",
                    "sha256": None,
                    "metadata": {},
                },
                "measurement_frames": [],
                "calibration": {
                    "coordinate_system": "MAT_XY_MM",
                    "mat_id": "MAT-R4-001",
                    "homography": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                    "quality": 1.0,
                },
            }
        ],
    }


def _anchor(anchor_id: str, x: float, y: float) -> dict:
    return {
        "anchor_id": anchor_id,
        "view_id": "VIEW-FRONT-001",
        "reference_frame_id": "A-FRONT-CLEAN-001",
        "coordinate_space": "IMAGE_PX",
        "x": x,
        "y": y,
        "feature_id": None,
    }


def _package(measurement: dict) -> dict:
    return {
        "schema_version": "mrea.measurement-package.v1",
        "measurement_package_id": "MP-R4-UNCERTAINTY-001",
        "project_id": "P-R4-UNCERTAINTY-001",
        "part_id": "PART-R4-UNCERTAINTY-001",
        "capture_package_id": "CP-R4-UNCERTAINTY-001",
        "measurements": [measurement],
    }


def _measurement(
    *,
    measurement_id: str,
    measurement_type: str,
    value: float,
    unit: str,
    anchors: list[dict],
    uncertainty: float | None | object = ...,
) -> dict:
    item = {
        "measurement_id": measurement_id,
        "type": measurement_type,
        "value": value,
        "unit": unit,
        "source": "MANUAL_MEASURED",
        "view_id": "VIEW-FRONT-001",
        "anchors": anchors,
        "verified": True,
    }
    if uncertainty is not ...:
        item["uncertainty"] = uncertainty
    return item


def _build(measurement: dict, entities: tuple[PointEntity, ...]):
    normalized = CanonicalInputAdapter().from_packages(_capture(), _package(measurement))
    draft = GeometryPipeline().build(entities, normalized.measurements)
    assert draft.unresolved == ()
    assert len(draft.dimensions) == 1
    return normalized.measurements[0], draft.dimensions[0]


def test_mm_uncertainty_is_preserved_without_conversion() -> None:
    measurement, dimension = _build(
        _measurement(
            measurement_id="M-MM",
            measurement_type="LINEAR_EXTERNAL",
            value=10.0,
            unit="mm",
            uncertainty=0.02,
            anchors=[_anchor("A-1", 0.0, 0.0), _anchor("A-2", 10.0, 0.0)],
        ),
        (
            PointEntity("P-1", Point2D(0.0, 0.0), confidence=0.99),
            PointEntity("P-2", Point2D(10.0, 0.0), confidence=0.99),
        ),
    )

    assert measurement.value == pytest.approx(10.0)
    assert measurement.unit == "mm"
    assert measurement.uncertainty == pytest.approx(0.02)
    assert dimension.value == pytest.approx(10.0)
    assert dimension.unit == "mm"
    assert dimension.uncertainty == pytest.approx(0.02)


def test_absent_uncertainty_remains_none_instead_of_getting_a_default() -> None:
    measurement, dimension = _build(
        _measurement(
            measurement_id="M-DEPTH",
            measurement_type="DEPTH",
            value=3.2,
            unit="mm",
            anchors=[_anchor("A-DEPTH", 5.0, 5.0)],
        ),
        (PointEntity("P-DEPTH", Point2D(5.0, 5.0), confidence=0.99),),
    )

    assert measurement.uncertainty is None
    assert dimension.uncertainty is None


def test_degree_three_anchor_uncertainty_is_preserved_without_conversion() -> None:
    measurement, dimension = _build(
        _measurement(
            measurement_id="M-ANGLE",
            measurement_type="ANGLE",
            value=90.0,
            unit="deg",
            uncertainty=0.5,
            anchors=[
                _anchor("A-A", 10.0, 40.0),
                _anchor("A-B", 30.0, 60.0),
                _anchor("A-C", 50.0, 40.0),
            ],
        ),
        (
            PointEntity("P-A", Point2D(10.0, 40.0), confidence=0.99),
            PointEntity("P-B", Point2D(30.0, 60.0), confidence=0.99),
            PointEntity("P-C", Point2D(50.0, 40.0), confidence=0.99),
        ),
    )

    assert len(measurement.anchors) == 3
    assert measurement.value == pytest.approx(90.0)
    assert measurement.unit == "deg"
    assert measurement.uncertainty == pytest.approx(0.5)
    assert dimension.unit == "deg"
    assert dimension.uncertainty == pytest.approx(0.5)


@pytest.mark.parametrize("invalid", [float("inf"), float("-inf"), float("nan"), "not-a-number", -0.1])
def test_malformed_uncertainty_fails_closed(invalid: object) -> None:
    item = _measurement(
        measurement_id="M-BAD",
        measurement_type="DEPTH",
        value=1.0,
        unit="mm",
        uncertainty=invalid,
        anchors=[_anchor("A-BAD", 0.0, 0.0)],
    )

    with pytest.raises(ValueError, match="uncertainty"):
        CanonicalInputAdapter().from_packages(_capture(), _package(item))


def test_zero_uncertainty_is_preserved_as_zero() -> None:
    item = _measurement(
        measurement_id="M-ZERO",
        measurement_type="DEPTH",
        value=1.0,
        unit="mm",
        uncertainty=0.0,
        anchors=[_anchor("A-ZERO", 0.0, 0.0)],
    )
    normalized = CanonicalInputAdapter().from_packages(_capture(), _package(copy.deepcopy(item)))
    assert normalized.measurements[0].uncertainty == 0.0
