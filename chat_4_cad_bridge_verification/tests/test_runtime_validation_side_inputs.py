from __future__ import annotations

import copy
import unittest

from mrea_cad_bridge.pipeline import execute_cad_transfer_v1
from mrea_cad_bridge.runtime_evidence import CadRuntimeEvidenceError
from mrea_cad_bridge.runtime_validation import evaluate_solidworks_runtime_inputs_v1
from mrea_cad_bridge.solidworks_runtime_inputs import (
    SOLIDWORKS_RUNTIME_ADAPTER_NAME,
    SOLIDWORKS_RUNTIME_INPUTS_PRODUCER,
    SOLIDWORKS_RUNTIME_INPUTS_SCHEMA,
)
from mrea_cad_bridge.test_double import TestDoubleCadAdapter


SKETCH_ID = "SP-PASS5-SIDE-001"
CAD_ID = "CAD-PASS5-SIDE-001"
REPORT_ID = "VR-PASS5-SIDE-001"
NATIVE_SHA = "b" * 64
REQUIRED_CODES = (
    "OS_WINDOWS_11_X64",
    "PROCESS_X64",
    "DOTNET_FRAMEWORK_48",
    "AGENT_EXECUTABLE_AVAILABLE",
    "SOLIDWORKS_COM_REGISTERED",
    "SOLIDWORKS_VERSION_2026",
    "SOLIDWORKS_INTEROP_AVAILABLE",
    "OUTPUT_PATH_WRITABLE",
    "PART_TEMPLATE_AVAILABLE",
)


def sketch_package() -> dict:
    return {
        "schema_version": "mrea.sketch-package.v1",
        "sketch_package_id": SKETCH_ID,
        "project_id": "P-PASS5-SIDE-001",
        "part_id": "PART-PASS5-SIDE-001",
        "view_id": "VIEW-FRONT-PASS5-SIDE-001",
        "coordinate_system": "MAT_XY_MM",
        "entities": [
            {
                "entity_id": "L-WIDTH",
                "type": "LINE",
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 80.2, "y": 0.0},
            }
        ],
        "dimensions": [
            {
                "dimension_id": "D-WIDTH",
                "measurement_id": "M-WIDTH",
                "type": "DISTANCE",
                "value": 80.2,
                "unit": "mm",
                "entity_ids": ["L-WIDTH"],
                "verified": True,
            }
        ],
        "constraints": [],
        "unresolved": [],
        "source_view_ids": ["VIEW-FRONT-PASS5-SIDE-001"],
    }


def canonical_report() -> dict:
    return execute_cad_transfer_v1(
        sketch_package=sketch_package(),
        adapter=TestDoubleCadAdapter(),
        cad_package_id=CAD_ID,
        report_id=REPORT_ID,
    ).cad_verification_report


def readiness() -> dict:
    checks = []
    for code in REQUIRED_CODES:
        item = {
            "code": code,
            "status": "PASS",
            "message": "ok",
            "required": True,
        }
        if code == "SOLIDWORKS_VERSION_2026":
            item["details"] = {
                "revision_number": "34.0.0",
                "revision_major": 34,
                "expected_revision_major": 34,
            }
        checks.append(item)
    return {
        "schema_version": "mrea.cad-host-readiness.v1",
        "adapter_name": SOLIDWORKS_RUNTIME_ADAPTER_NAME,
        "status": "READY",
        "checks": checks,
    }


def successful_inputs() -> dict:
    return {
        "schema_version": SOLIDWORKS_RUNTIME_INPUTS_SCHEMA,
        "producer": SOLIDWORKS_RUNTIME_INPUTS_PRODUCER,
        "adapter_name": SOLIDWORKS_RUNTIME_ADAPTER_NAME,
        "host_readiness": readiness(),
        "agent_exit_code": 0,
        "real_host_executed": True,
        "solidworks_version": "34.0.0",
        "sketch_package_id": SKETCH_ID,
        "bindings": [
            {
                "dimension_id": "D-WIDTH",
                "measurement_id": "M-WIDTH",
                "vendor_dimension_ref": "D1@Sketch1",
            }
        ],
        "read_back_dimensions": [
            {
                "dimension_id": "D-WIDTH",
                "actual_value": 80.2,
                "unit": "mm",
            }
        ],
        "constraint_conflicts": [],
        "artifacts": [
            {
                "artifact_id": "SWPART-PASS5-001",
                "kind": "SOLIDWORKS_PART",
                "uri": "file:///controlled/PASS5.SLDPRT",
                "media_type": "application/octet-stream",
                "sha256": NATIVE_SHA,
            }
        ],
        "diagnostics": [],
        "canonical_verification_report": canonical_report(),
    }


def version_check(payload: dict) -> dict:
    return next(
        item
        for item in payload["host_readiness"]["checks"]
        if item["code"] == "SOLIDWORKS_VERSION_2026"
    )


class SolidWorksRuntimeValidationSideInputsTests(unittest.TestCase):
    def test_successful_side_bundle_replays_through_direct_runtime_path(self) -> None:
        result = evaluate_solidworks_runtime_inputs_v1(
            sketch_package=sketch_package(),
            runtime_inputs=successful_inputs(),
        )
        self.assertIsNotNone(result.transfer_execution)
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.runtime_status, "VERIFIED")
        self.assertEqual(result.runtime_inputs.solidworks_version, "34.0.0")

    def test_worker_revision_major_mismatch_is_rejected(self) -> None:
        payload = successful_inputs()
        payload["solidworks_version"] = "35.0.0"
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            evaluate_solidworks_runtime_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_VERSION_MAJOR_MISMATCH",
        )

    def test_host_and_worker_revision_number_must_match(self) -> None:
        payload = successful_inputs()
        version_check(payload)["details"]["revision_number"] = "34.1.0"
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            evaluate_solidworks_runtime_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_VERSION_EVIDENCE_MISMATCH",
        )

    def test_host_revision_major_must_match_worker(self) -> None:
        payload = successful_inputs()
        version_check(payload)["details"]["revision_major"] = 33
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            evaluate_solidworks_runtime_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_VERSION_EVIDENCE_MISMATCH",
        )

    def test_malformed_constraint_conflict_is_rejected_without_string_coercion(self) -> None:
        payload = successful_inputs()
        payload["constraint_conflicts"] = [123]
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            evaluate_solidworks_runtime_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(captured.exception.code, "SOLIDWORKS_RUNTIME_CONFLICTS_INVALID")

    def test_nonzero_exit_remains_evidence_only_without_transfer_replay(self) -> None:
        payload = successful_inputs()
        payload["agent_exit_code"] = 40
        payload["canonical_verification_report"] = None
        payload["bindings"] = []
        payload["read_back_dimensions"] = []
        payload["artifacts"] = []
        result = evaluate_solidworks_runtime_inputs_v1(
            sketch_package=sketch_package(),
            runtime_inputs=payload,
        )
        self.assertIsNone(result.transfer_execution)
        self.assertIsNone(result.verification_status)
        self.assertEqual(result.runtime_status, "FAILED")

    def test_tampered_canonical_report_still_fails_existing_primary_bridge(self) -> None:
        payload = successful_inputs()
        payload["canonical_verification_report"] = copy.deepcopy(
            payload["canonical_verification_report"]
        )
        payload["canonical_verification_report"]["items"][0]["actual"] = 80.3
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            evaluate_solidworks_runtime_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(captured.exception.code, "SOLIDWORKS_CANONICAL_REPORT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
