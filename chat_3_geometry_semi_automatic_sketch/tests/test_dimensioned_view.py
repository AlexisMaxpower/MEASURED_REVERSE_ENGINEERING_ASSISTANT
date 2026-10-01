from __future__ import annotations

import copy
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from mrea_geometry import DimensionedViewRenderer, ReferenceImageLayer


ROOT = Path(__file__).resolve().parent
VISION_FIXTURES = ROOT / "fixtures" / "vision"
VIEW_FIXTURES = ROOT / "fixtures" / "dimensioned_view"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _front_package() -> dict:
    return _load(VISION_FIXTURES / "front_plate_sketch_golden.json")


def test_front_plate_dimensioned_view_matches_exact_golden() -> None:
    package = _front_package()
    artifact = DimensionedViewRenderer().render(package)
    expected = (VIEW_FIXTURES / "front_plate_dimensioned_view.svg").read_text(encoding="utf-8")

    assert artifact.svg == expected
    assert artifact.sketch_package_id == "SP-VISION-001"
    assert artifact.dimension_ids == (
        "D-V-CENTER",
        "D-V-HEIGHT",
        "D-V-HOLE",
        "D-V-WIDTH",
    )
    assert artifact.measurement_ids == (
        "M-V-CENTER",
        "M-V-HEIGHT",
        "M-V-HOLE",
        "M-V-WIDTH",
    )


def test_svg_is_well_formed_and_exposes_traceability() -> None:
    artifact = DimensionedViewRenderer().render(_front_package())
    root = ElementTree.fromstring(artifact.svg)

    assert root.tag.endswith("svg")
    assert 'data-measurement-id="M-V-WIDTH"' in artifact.svg
    assert 'data-provenance="MANUAL_MEASURED"' in artifact.svg
    assert 'data-verified="true"' in artifact.svg
    assert "VISION_DETECTED | confidence=0.990" in artifact.svg
    assert "Geometry: VISION_DETECTED · confidence 0.766–0.990" in artifact.svg
    assert "CONSTRAINT_BELOW_PROMOTION_CONFIDENCE" in artifact.svg


def test_reference_image_requires_explicit_mat_bounds_and_is_rendered_without_guessing() -> None:
    package = _front_package()
    layer = ReferenceImageLayer(
        href="fixture://images/front_plate_clean.png",
        min_x_mm=0.0,
        min_y_mm=0.0,
        max_x_mm=40.0,
        max_y_mm=20.0,
        opacity=0.25,
    )
    artifact = DimensionedViewRenderer().render(package, reference_image=layer)

    assert 'id="clean-reference"' in artifact.svg
    assert 'href="fixture://images/front_plate_clean.png"' in artifact.svg
    assert 'opacity="0.25"' in artifact.svg
    assert 'preserveAspectRatio="none"' in artifact.svg

    with pytest.raises(ValueError, match="positive area"):
        ReferenceImageLayer(
            href="fixture://bad.png",
            min_x_mm=1.0,
            min_y_mm=0.0,
            max_x_mm=1.0,
            max_y_mm=10.0,
        )


def test_renderer_is_read_only_and_deterministic() -> None:
    package = _front_package()
    original = copy.deepcopy(package)
    renderer = DimensionedViewRenderer()

    first = renderer.render(package)
    second = renderer.render(copy.deepcopy(package))

    assert first == second
    assert package == original


def test_all_v1_primitive_and_dimension_visuals_are_supported() -> None:
    package = {
        "schema_version": "mrea.sketch-package.v1",
        "sketch_package_id": "SP-ALL-001",
        "project_id": "P",
        "part_id": "PART",
        "view_id": "VIEW",
        "coordinate_system": "MAT_XY_MM",
        "entities": [
            {
                "entity_id": "P1",
                "type": "POINT",
                "point": {"x": 1.0, "y": 1.0},
                "provenance": "GEOMETRY_DERIVED",
                "confidence": 0.8,
            },
            {
                "entity_id": "L1",
                "type": "LINE",
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 20.0, "y": 0.0},
                "provenance": "GEOMETRY_DERIVED",
                "confidence": 1.0,
            },
            {
                "entity_id": "L2",
                "type": "LINE",
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 0.0, "y": 20.0},
                "provenance": "GEOMETRY_DERIVED",
                "confidence": 1.0,
            },
            {
                "entity_id": "C1",
                "type": "CIRCLE",
                "center": {"x": 10.0, "y": 10.0},
                "radius": 3.0,
                "provenance": "VISION_DETECTED",
                "confidence": 0.9,
            },
            {
                "entity_id": "A1",
                "type": "ARC",
                "center": {"x": 15.0, "y": 15.0},
                "radius": 4.0,
                "start_angle_deg": 0.0,
                "end_angle_deg": 120.0,
                "provenance": "VISION_DETECTED",
                "confidence": 0.85,
            },
        ],
        "constraints": [],
        "dimensions": [
            {
                "dimension_id": "D-DIST",
                "measurement_id": "M-DIST",
                "type": "DISTANCE",
                "value": 20.0,
                "unit": "mm",
                "entity_ids": ["L1"],
                "verified": True,
                "provenance": "MANUAL_MEASURED",
            },
            {
                "dimension_id": "D-DIA",
                "measurement_id": "M-DIA",
                "type": "DIAMETER",
                "value": 6.0,
                "unit": "mm",
                "entity_ids": ["C1"],
                "verified": True,
                "provenance": "DEVICE_REPORTED",
            },
            {
                "dimension_id": "D-RAD",
                "measurement_id": "M-RAD",
                "type": "RADIUS",
                "value": 4.0,
                "unit": "mm",
                "entity_ids": ["A1"],
                "verified": True,
                "provenance": "MANUAL_MEASURED",
            },
            {
                "dimension_id": "D-ANG",
                "measurement_id": "M-ANG",
                "type": "ANGLE",
                "value": 90.0,
                "unit": "deg",
                "entity_ids": ["L1", "L2"],
                "verified": True,
                "provenance": "MANUAL_MEASURED",
            },
        ],
        "unresolved": [],
        "source_view_ids": ["VIEW"],
    }

    svg = DimensionedViewRenderer(scale_px_per_mm=5.0).render(package).svg

    assert 'class="geometry-point"' in svg
    assert 'class="geometry-line"' in svg
    assert 'class="geometry-circle"' in svg
    assert 'class="geometry-arc"' in svg
    assert "Ø6 mm" in svg
    assert "R4 mm" in svg
    assert "90 deg" in svg


def test_invalid_or_untraceable_inputs_fail_closed() -> None:
    package = _front_package()

    wrong_space = copy.deepcopy(package)
    wrong_space["coordinate_system"] = "IMAGE_PX"
    with pytest.raises(ValueError, match="MAT_XY_MM"):
        DimensionedViewRenderer().render(wrong_space)

    missing_entity = copy.deepcopy(package)
    missing_entity["dimensions"][0]["entity_ids"] = ["DOES-NOT-EXIST"]
    with pytest.raises(ValueError, match="missing entities"):
        DimensionedViewRenderer().render(missing_entity)
