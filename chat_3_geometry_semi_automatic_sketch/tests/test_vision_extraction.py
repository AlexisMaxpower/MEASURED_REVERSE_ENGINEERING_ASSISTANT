from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
FIXTURES = ROOT / "tests/fixtures/vision"
sys.path.insert(0, str(ROOT / "src"))

from mrea_geometry import (
    CanonicalInputAdapter,
    GeometryPipeline,
    ImageGeometryExtractor,
    VisionGeometryPipeline,
)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _capture() -> dict:
    return _load("vision_capture_package.json")


def _measurement_package() -> dict:
    return _load("vision_measurement_package.json")


def _homography() -> list[float]:
    return _capture()["views"][0]["calibration"]["homography"]


def _build_vision_sketch() -> tuple[dict, object, object]:
    capture = _capture()
    measurements = _measurement_package()
    context = CanonicalInputAdapter().from_packages(capture, measurements)
    extraction = ImageGeometryExtractor().extract_profile(
        FIXTURES / "front_plate_reference.pbm",
        capture["views"][0]["calibration"]["homography"],
    )
    draft = GeometryPipeline().build(extraction.primitives, context.measurements)
    sketch = VisionGeometryPipeline().build_sketch(
        extraction, context, sketch_package_id="SP-VISION-001"
    )
    return sketch, extraction, draft


def _validate_sketch(package: dict) -> None:
    schema = json.loads(
        (REPO_ROOT / "core/contracts/mrea_contracts_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": "#/$defs/SketchPackage",
    }
    Draft202012Validator(validator_schema).validate(package)


def test_reference_image_pipeline_matches_golden_sketch_exactly() -> None:
    sketch, extraction, draft = _build_vision_sketch()

    assert extraction.issues == ()
    assert draft.unresolved == ()
    assert draft.conflicts == ()
    assert sketch == _load("front_plate_sketch_golden.json")
    _validate_sketch(sketch)


def test_detected_geometry_has_truthful_vision_provenance() -> None:
    sketch, _, _ = _build_vision_sketch()

    assert sketch["entities"]
    assert {entity["provenance"] for entity in sketch["entities"]} == {
        "VISION_DETECTED"
    }
    assert all(entity["confidence"] < 1.0 for entity in sketch["entities"])


def test_verified_measurement_values_survive_vision_binding_unchanged() -> None:
    sketch, _, _ = _build_vision_sketch()
    expected = {
        "M-V-WIDTH": 40.0,
        "M-V-HEIGHT": 20.0,
        "M-V-HOLE": 8.0,
        "M-V-CENTER": 20.0,
    }

    assert {item["measurement_id"]: item["value"] for item in sketch["dimensions"]} == expected
    assert all(item["verified"] is True for item in sketch["dimensions"])
    assert {item["provenance"] for item in sketch["dimensions"]} == {
        "MANUAL_MEASURED"
    }


def test_profile_extraction_is_deterministic_across_repeated_runs() -> None:
    extractor = ImageGeometryExtractor()
    first = extractor.extract_profile(FIXTURES / "front_plate_reference.pbm", _homography())
    second = extractor.extract_profile(FIXTURES / "front_plate_reference.pbm", _homography())

    assert first == second


def test_projective_transform_keeps_lines_but_does_not_invent_circles() -> None:
    projective = [0.5, 0.0, -5.0, 0.0, -0.5, 25.0, 0.001, 0.0, 1.0]
    result = ImageGeometryExtractor().extract_profile(
        FIXTURES / "front_plate_reference.pbm", projective
    )

    assert any(primitive.kind == "LINE" for primitive in result.primitives)
    assert not any(primitive.kind == "CIRCLE" for primitive in result.primitives)
    assert [issue.code for issue in result.issues] == [
        "CIRCLE_REQUIRES_SIMILARITY_TRANSFORM",
        "CIRCLE_REQUIRES_SIMILARITY_TRANSFORM",
    ]


def test_unsupported_profile_stays_explicit_unresolved() -> None:
    result = ImageGeometryExtractor().extract_profile(
        FIXTURES / "open_arc_reference.pbm",
        [1.0, 0.0, -5.0, 0.0, -1.0, 5.0, 0.0, 0.0, 1.0],
    )

    assert result.primitives == ()
    assert result.issues
    assert result.issues[0].code in {
        "NO_DOMINANT_REFERENCE_CONTOUR",
        "UNSUPPORTED_OUTER_CONTOUR",
    }


def test_candidate_issue_projects_to_canonical_sketch_unresolved() -> None:
    capture = _capture()
    context = CanonicalInputAdapter().from_packages(
        capture,
        {
            "schema_version": "mrea.measurement-package.v1",
            "measurement_package_id": "MP-VISION-EMPTY",
            "project_id": capture["project_id"],
            "part_id": capture["part_id"],
            "capture_package_id": capture["capture_package_id"],
            "measurements": [],
        },
    )
    extraction = ImageGeometryExtractor().extract_profile(
        FIXTURES / "open_arc_reference.pbm",
        [1.0, 0.0, -5.0, 0.0, -1.0, 5.0, 0.0, 0.0, 1.0],
    )
    sketch = VisionGeometryPipeline().build_sketch(
        extraction, context, sketch_package_id="SP-VISION-UNRESOLVED"
    )

    assert sketch["unresolved"]
    assert sketch["unresolved"][0]["code"] == extraction.issues[0].code
    _validate_sketch(sketch)


def test_open_arc_fixture_matches_golden_geometry_exactly() -> None:
    result = ImageGeometryExtractor().extract_open_arcs(
        FIXTURES / "open_arc_reference.pbm",
        [1.0, 0.0, -5.0, 0.0, -1.0, 5.0, 0.0, 0.0, 1.0],
    )
    actual = {
        "primitives": [item.to_dict() for item in result.primitives],
        "issues": [item.to_dict() for item in result.issues],
    }

    assert actual == _load("open_arc_geometry_golden.json")
    assert actual["primitives"][0]["source"] == "VISION_DETECTED"
