from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "core" / "contracts" / "mrea_contracts_v1.schema.json"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"

CASES = {
    "project_v1.json": "ProjectContract",
    "capture_package_v1.json": "CapturePackage",
    "measurement_package_v1.json": "MeasurementPackage",
    "sketch_package_v1.json": "SketchPackage",
    "cad_package_v1.json": "CADPackage",
    "cad_verification_v1.json": "CADVerificationReport",
    "lifecycle_event_v1.json": "LifecycleEvent",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def root_schema() -> dict:
    return _load(SCHEMA_PATH)


@pytest.mark.parametrize(("fixture_name", "definition_name"), CASES.items())
def test_canonical_fixture_matches_owned_schema(root_schema: dict, fixture_name: str, definition_name: str) -> None:
    scoped = {"$schema": root_schema["$schema"], "$defs": root_schema["$defs"], "$ref": f"#/$defs/{definition_name}"}
    Draft202012Validator(scoped, format_checker=FormatChecker()).validate(_load(FIXTURE_ROOT / fixture_name))


def test_golden_contract_chain_ids_are_consistent() -> None:
    project = _load(FIXTURE_ROOT / "project_v1.json")
    capture = _load(FIXTURE_ROOT / "capture_package_v1.json")
    measurements = _load(FIXTURE_ROOT / "measurement_package_v1.json")
    sketch = _load(FIXTURE_ROOT / "sketch_package_v1.json")
    cad = _load(FIXTURE_ROOT / "cad_package_v1.json")
    verification = _load(FIXTURE_ROOT / "cad_verification_v1.json")
    assert capture["project_id"] == project["project_id"]
    assert capture["part_id"] == project["part_id"]
    assert measurements["project_id"] == project["project_id"]
    assert measurements["part_id"] == project["part_id"]
    assert measurements["capture_package_id"] == capture["capture_package_id"]
    assert sketch["project_id"] == project["project_id"]
    assert sketch["part_id"] == project["part_id"]
    assert cad["sketch_package_id"] == sketch["sketch_package_id"]
    assert verification["cad_package_id"] == cad["cad_package_id"]
    assert verification["sketch_package_id"] == sketch["sketch_package_id"]
