from __future__ import annotations

import json
import sys
from pathlib import Path

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
    PointEntity,
    SketchPackageBuilder,
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_files() -> tuple[dict, dict, dict, dict]:
    capture = _json(REPO_ROOT / "tests/fixtures/contracts/capture_package_v1.json")
    measurements = _json(REPO_ROOT / "tests/fixtures/contracts/measurement_package_v1.json")
    expected = _json(REPO_ROOT / "tests/fixtures/contracts/sketch_package_v1.json")
    schema = _json(REPO_ROOT / "core/contracts/mrea_contracts_v1.schema.json")
    return capture, measurements, expected, schema


def _golden_primitives() -> tuple:
    data = _json(ROOT / "tests/fixtures/internal/front_golden_primitives.json")
    result = []
    for item in data["primitives"]:
        if item["kind"] == "LINE":
            result.append(
                Line(
                    entity_id=item["entity_id"],
                    start=Point2D(*item["start"]),
                    end=Point2D(*item["end"]),
                    feature_id=item.get("feature_id"),
                    source=item["source"],
                    confidence=item.get("confidence"),
                )
            )
        elif item["kind"] == "CIRCLE":
            result.append(
                Circle(
                    entity_id=item["entity_id"],
                    center=Point2D(*item["center"]),
                    radius=item["radius"],
                    feature_id=item.get("feature_id"),
                    source=item["source"],
                    confidence=item.get("confidence"),
                )
            )
        else:
            raise AssertionError(f"unsupported golden primitive kind: {item['kind']}")
    return tuple(result)


def _validate_sketch(package: dict, schema: dict) -> None:
    validator_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": "#/$defs/SketchPackage",
    }
    Draft202012Validator(validator_schema).validate(package)


def _build_front(primitives: tuple | None = None) -> tuple[dict, dict]:
    capture, measurements, expected, schema = _canonical_files()
    context = CanonicalInputAdapter().from_packages(capture, measurements)
    draft = GeometryPipeline().build(primitives or _golden_primitives(), context.measurements)
    actual = SketchPackageBuilder().build(
        draft,
        context,
        sketch_package_id="SP-GOLDEN-001",
    )
    _validate_sketch(actual, schema)
    return actual, expected


def test_canonical_front_pipeline_matches_integrator_golden_fixture_exactly():
    actual, expected = _build_front()
    assert actual == expected


def test_canonical_front_pipeline_is_deterministic_for_primitive_order():
    primitives = _golden_primitives()
    first, _ = _build_front(primitives)
    second, _ = _build_front(tuple(reversed(primitives)))
    assert first == second


def test_verified_measurement_links_are_preserved_in_canonical_dimensions():
    actual, _ = _build_front()
    assert [item["measurement_id"] for item in actual["dimensions"]] == [
        "M-WIDTH",
        "M-HEIGHT",
        "M-HOLE",
        "M-CENTER",
    ]
    assert all(item["verified"] for item in actual["dimensions"])


def test_point_is_supported_by_v1_canonical_entity_builder_and_schema():
    capture, measurements, _, schema = _canonical_files()
    context = CanonicalInputAdapter().from_packages(capture, measurements)
    draft = GeometryPipeline().build(
        (
            PointEntity(
                entity_id="P-TEST",
                point=Point2D(1.0, 2.0),
                source="GEOMETRY_DERIVED",
                confidence=1.0,
            ),
        ),
        (),
    )
    package = SketchPackageBuilder().build(
        draft,
        context,
        sketch_package_id="SP-POINT-TEST",
    )
    _validate_sketch(package, schema)
    assert package["entities"] == [
        {
            "entity_id": "P-TEST",
            "type": "POINT",
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
            "point": {"x": 1.0, "y": 2.0},
        }
    ]
