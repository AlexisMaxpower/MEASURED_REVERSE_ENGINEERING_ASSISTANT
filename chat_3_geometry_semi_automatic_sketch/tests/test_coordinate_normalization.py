from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from mrea_geometry import (
    CanonicalInputAdapter,
    Circle,
    GeometryPipeline,
    Line,
    Point2D,
    SketchPackageBuilder,
)


def _chat2_package() -> dict:
    return json.loads(
        (ROOT / "tests/fixtures/internal/chat2_image_px_measurement_package.json").read_text(
            encoding="utf-8"
        )
    )


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "core/contracts/mrea_contracts_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _validate(definition: str, payload: dict) -> None:
    schema = _schema()
    Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
    ).validate(payload)


def _capture(*, homography: list[float] | None = None) -> dict:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-GOLDEN-001",
        "project_id": "P-GOLDEN-001",
        "part_id": "PART-GOLDEN-001",
        "views": [
            {
                "view_id": "VIEW-FRONT-001",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "A-FRONT-CLEAN-001",
                    "kind": "CLEAN_REFERENCE_IMAGE",
                    "uri": "fixture://images/front_clean.png",
                    "media_type": "image/png",
                    "sha256": None,
                    "metadata": {"width_px": 1604, "height_px": 842},
                },
                "measurement_frames": [],
                "calibration": (
                    None
                    if homography is None
                    else {
                        "coordinate_system": "MAT_XY_MM",
                        "mat_id": "MAT-A4-V1",
                        "homography": homography,
                        "quality": 1.0,
                    }
                ),
            }
        ],
    }


def _scale_homography() -> list[float]:
    return [0.1, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 1.0]


def _front_primitives() -> tuple:
    return (
        Line(
            "L-BOTTOM",
            Point2D(0.0, 0.0),
            Point2D(80.2, 0.0),
            "EDGE_BOTTOM",
            "GEOMETRY_DERIVED",
            1.0,
        ),
        Line(
            "L-RIGHT",
            Point2D(80.2, 0.0),
            Point2D(80.2, 42.1),
            "EDGE_RIGHT",
            "GEOMETRY_DERIVED",
            1.0,
        ),
        Line(
            "L-TOP",
            Point2D(80.2, 42.1),
            Point2D(0.0, 42.1),
            "EDGE_TOP",
            "GEOMETRY_DERIVED",
            1.0,
        ),
        Line(
            "L-LEFT",
            Point2D(0.0, 42.1),
            Point2D(0.0, 0.0),
            "EDGE_LEFT",
            "GEOMETRY_DERIVED",
            1.0,
        ),
        Circle(
            "C-HOLE-1",
            Point2D(10.1, 21.05),
            2.55,
            "HOLE_1",
            "GEOMETRY_DERIVED",
            1.0,
        ),
        Circle(
            "C-HOLE-2",
            Point2D(70.1, 21.05),
            2.55,
            "HOLE_2",
            "GEOMETRY_DERIVED",
            1.0,
        ),
    )


def _build_from_chat2(package: dict | None = None) -> tuple[dict, object]:
    context = CanonicalInputAdapter().from_packages(
        _capture(homography=_scale_homography()), package or _chat2_package()
    )
    draft = GeometryPipeline().build(_front_primitives(), context.measurements)
    sketch = SketchPackageBuilder().build(
        draft, context, sketch_package_id="SP-IMAGEPX-001"
    )
    return sketch, context


def test_chat2_style_specimen_is_canonical_measurement_package() -> None:
    _validate("MeasurementPackage", _chat2_package())


def test_image_px_anchor_is_normalized_with_non_identity_homography() -> None:
    _, context = _build_from_chat2()
    measurement = context.measurements[0]

    assert measurement.measurement_id == "M-WIDTH-IMAGEPX"
    assert measurement.value == 80.2
    assert measurement.verified is True
    assert measurement.source == "MANUAL_MEASURED"
    assert [anchor.feature_id for anchor in measurement.anchors] == [None, None]
    assert [anchor.point for anchor in measurement.anchors] == [
        Point2D(0.0, 21.05),
        Point2D(80.2, 21.05),
    ]
    assert [anchor.reference_frame_id for anchor in measurement.anchors] == [
        "A-FRONT-CLEAN-001",
        "A-FRONT-CLEAN-001",
    ]
    assert [anchor.source_coordinate_space for anchor in measurement.anchors] == [
        "IMAGE_PX",
        "IMAGE_PX",
    ]


def test_chat2_style_image_px_package_reaches_schema_valid_sketch_package() -> None:
    sketch, _ = _build_from_chat2()
    _validate("SketchPackage", sketch)

    assert sketch["schema_version"] == "mrea.sketch-package.v1"
    assert sketch["coordinate_system"] == "MAT_XY_MM"
    assert sketch["unresolved"] == []
    assert sketch["dimensions"] == [
        {
            "dimension_id": "D-WIDTH-IMAGEPX",
            "measurement_id": "M-WIDTH-IMAGEPX",
            "type": "DISTANCE",
            "value": 80.2,
            "unit": "mm",
            "entity_ids": ["L-BOTTOM"],
            "verified": True,
            "provenance": "MANUAL_MEASURED",
        }
    ]


def test_projective_homogeneous_divide_is_applied() -> None:
    package = _chat2_package()
    anchor = package["measurements"][0]["anchors"][0]
    package["measurements"][0]["anchors"] = [anchor]
    anchor["x"] = 2.0
    anchor["y"] = 4.0

    context = CanonicalInputAdapter().from_packages(
        _capture(
            homography=[
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.5,
                0.0,
                1.0,
            ]
        ),
        package,
    )

    assert context.measurements[0].anchors[0].point == Point2D(1.0, 2.0)


def test_zero_homogeneous_divisor_is_rejected_explicitly() -> None:
    package = _chat2_package()
    anchor = package["measurements"][0]["anchors"][0]
    package["measurements"][0]["anchors"] = [anchor]
    anchor["x"] = 1.0
    anchor["y"] = 0.0

    with pytest.raises(ValueError, match="degenerate homogeneous divisor"):
        CanonicalInputAdapter().from_packages(
            _capture(
                homography=[
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    1.0,
                    0.0,
                    -1.0,
                ]
            ),
            package,
        )


def test_wrong_image_reference_frame_is_rejected() -> None:
    package = _chat2_package()
    package["measurements"][0]["anchors"][0]["reference_frame_id"] = "WRONG-REF"

    with pytest.raises(ValueError, match="reference_frame_id does not match"):
        CanonicalInputAdapter().from_packages(
            _capture(homography=_scale_homography()), package
        )


def test_image_px_without_calibration_is_rejected_explicitly() -> None:
    with pytest.raises(ValueError, match="require view calibration"):
        CanonicalInputAdapter().from_packages(_capture(homography=None), _chat2_package())


def test_degenerate_homography_is_rejected_explicitly() -> None:
    with pytest.raises(ValueError, match="homography is degenerate"):
        CanonicalInputAdapter().from_packages(
            _capture(homography=[0.0] * 9), _chat2_package()
        )


def test_mat_xy_mm_anchor_passes_through_without_calibration_lookup() -> None:
    package = _chat2_package()
    anchor = package["measurements"][0]["anchors"][0]
    package["measurements"][0]["anchors"] = [anchor]
    anchor["coordinate_space"] = "MAT_XY_MM"
    anchor["x"] = 12.5
    anchor["y"] = 7.25

    context = CanonicalInputAdapter().from_packages(_capture(homography=None), package)
    normalized = context.measurements[0].anchors[0]

    assert normalized.point == Point2D(12.5, 7.25)
    assert normalized.source_coordinate_space == "MAT_XY_MM"


def test_image_px_flow_is_deterministic() -> None:
    first, _ = _build_from_chat2()
    package = copy.deepcopy(_chat2_package())
    package["measurements"][0]["anchors"].reverse()
    second, _ = _build_from_chat2(package)

    assert first == second
