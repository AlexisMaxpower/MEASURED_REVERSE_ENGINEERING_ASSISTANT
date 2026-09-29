from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from mrea_geometry import (
    CanonicalInputAdapter,
    Circle,
    GeometryPipeline,
    Line,
    Point2D,
    SketchPackageBuilder,
)
from mrea_cad_bridge import TestDoubleCadAdapter, execute_cad_transfer_v1

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"
CHAT3_INTERNAL = (
    REPO_ROOT
    / "chat_3_geometry_semi_automatic_sketch"
    / "tests"
    / "fixtures"
    / "internal"
    / "front_golden_primitives.json"
)
SCHEMA_PATH = REPO_ROOT / "core" / "contracts" / "mrea_contracts_v1.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(definition_name: str) -> Draft202012Validator:
    root = _load(SCHEMA_PATH)
    return Draft202012Validator(
        {
            "$schema": root["$schema"],
            "$defs": root["$defs"],
            "$ref": f"#/$defs/{definition_name}",
        },
        format_checker=FormatChecker(),
    )


def _chat3_primitives() -> tuple:
    source = _load(CHAT3_INTERNAL)
    result = []
    for item in source["primitives"]:
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
            raise AssertionError(f"unsupported integration primitive: {item['kind']}")
    return tuple(result)


def test_real_chat3_sketch_package_is_consumed_and_verified_by_chat4() -> None:
    capture = _load(FIXTURE_ROOT / "capture_package_v1.json")
    measurements = _load(FIXTURE_ROOT / "measurement_package_v1.json")

    context = CanonicalInputAdapter().from_packages(capture, measurements)
    draft = GeometryPipeline().build(_chat3_primitives(), context.measurements)
    sketch_package = SketchPackageBuilder().build(
        draft,
        context,
        sketch_package_id="SP-XSLICE34-001",
    )
    _validator("SketchPackage").validate(sketch_package)

    transfer = execute_cad_transfer_v1(
        sketch_package=sketch_package,
        adapter=TestDoubleCadAdapter(),
        cad_package_id="CAD-XSLICE34-001",
        report_id="CADV-XSLICE34-001",
    )

    _validator("CADPackage").validate(transfer.cad_package)
    _validator("CADVerificationReport").validate(transfer.cad_verification_report)

    assert transfer.cad_package["sketch_package_id"] == sketch_package["sketch_package_id"]
    assert transfer.cad_verification_report["sketch_package_id"] == sketch_package["sketch_package_id"]
    assert transfer.cad_verification_report["cad_package_id"] == transfer.cad_package["cad_package_id"]
    assert transfer.cad_verification_report["overall_status"] == "VERIFIED"

    sketch_measurement_ids = {
        item["measurement_id"]
        for item in sketch_package["dimensions"]
        if item.get("measurement_id") is not None
    }
    verified_measurement_ids = {
        item["measurement_id"]
        for item in transfer.cad_verification_report["items"]
        if item.get("measurement_id") is not None
    }
    assert verified_measurement_ids == sketch_measurement_ids
    assert all(
        item["status"] == "VERIFIED"
        for item in transfer.cad_verification_report["items"]
    )
