from __future__ import annotations

import copy
import unittest

from mrea_cad_bridge.pipeline import execute_cad_transfer_v1
from mrea_cad_bridge.runtime_evidence import CadRuntimeEvidenceError
from mrea_cad_bridge.solidworks_runtime_inputs import (
    SOLIDWORKS_RUNTIME_ADAPTER_NAME,
    SOLIDWORKS_RUNTIME_INPUTS_PRODUCER,
    SOLIDWORKS_RUNTIME_INPUTS_SCHEMA,
    build_solidworks_runtime_evidence_from_inputs_v1,
    parse_solidworks_runtime_inputs_v1,
)
from mrea_cad_bridge.test_double import TestDoubleCadAdapter


SKETCH_ID = "SP-PASS3-BRIDGE-001"
CAD_ID = "CAD-SW-PASS3-HOST-001"
REPORT_ID = "CADV-SW-PASS3-HOST-001"
NATIVE_SHA = "a" * 64
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
        "project_id": "P-PASS3-BRIDGE-001",
        "part_id": "PART-PASS3-BRIDGE-001",
        "view_id": "VIEW-FRONT-PASS3-BRIDGE-001",
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
        "source_view_ids": ["VIEW-FRONT-PASS3-BRIDGE-001"],
    }


def readiness() -> dict:
    return {
        "schema_version": "mrea.cad-host-readiness.v1",
        "adapter_name": SOLIDWORKS_RUNTIME_ADAPTER_NAME,
        "status": "READY",
        "checks": [
            {
                "code": code,
                "status": "PASS",
                "message": "ok",
                "required": True,
            }
            for code in REQUIRED_CODES
        ],
    }


def canonical_report() -> dict:
    execution = execute_cad_transfer_v1(
        sketch_package=sketch_package(),
        adapter=TestDoubleCadAdapter(),
        cad_package_id=CAD_ID,
        report_id=REPORT_ID,
    )
    return execution.cad_verification_report


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
                "artifact_id": "SWPART-PASS3-001",
                "kind": "SOLIDWORKS_PART",
                "uri": "file:///controlled/PART-PASS3-001.SLDPRT",
                "media_type": "application/octet-stream",
                "sha256": NATIVE_SHA,
            }
        ],
        "diagnostics": [],
        "canonical_verification_report": canonical_report(),
    }


class SolidWorksRuntimeInputsBridgeTests(unittest.TestCase):
    def test_valid_side_inputs_replay_into_primary_runtime_verified(self) -> None:
        evidence = build_solidworks_runtime_evidence_from_inputs_v1(
            sketch_package=sketch_package(),
            runtime_inputs=successful_inputs(),
        )
        self.assertEqual(evidence["schema_version"], "mrea.cad-runtime-evidence.v1")
        self.assertEqual(evidence["status"], "VERIFIED")
        self.assertEqual(evidence["verification_report"]["overall_status"], "VERIFIED")
        self.assertEqual(evidence["artifacts"][0]["sha256"], NATIVE_SHA)

    def test_side_final_status_is_forbidden(self) -> None:
        payload = successful_inputs()
        payload["status"] = "VERIFIED"
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            parse_solidworks_runtime_inputs_v1(payload)
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_FINAL_STATUS_FORBIDDEN",
        )

    def test_missing_mandatory_readiness_code_is_rejected(self) -> None:
        payload = successful_inputs()
        payload["host_readiness"]["checks"] = [
            item
            for item in payload["host_readiness"]["checks"]
            if item["code"] != "SOLIDWORKS_COM_REGISTERED"
        ]
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            parse_solidworks_runtime_inputs_v1(payload)
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_READINESS_CODES_MISSING",
        )

    def test_mandatory_readiness_code_cannot_be_optional(self) -> None:
        payload = successful_inputs()
        payload["host_readiness"]["checks"][0]["required"] = False
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            parse_solidworks_runtime_inputs_v1(payload)
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_READINESS_CODE_NOT_REQUIRED",
        )

    def test_sketch_identity_mismatch_is_rejected(self) -> None:
        payload = successful_inputs()
        payload["sketch_package_id"] = "SP-OTHER"
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            build_solidworks_runtime_evidence_from_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_SKETCH_ID_MISMATCH",
        )

    def test_tampered_side_canonical_report_is_rejected(self) -> None:
        payload = successful_inputs()
        payload["canonical_verification_report"] = copy.deepcopy(
            payload["canonical_verification_report"]
        )
        payload["canonical_verification_report"]["items"][0]["actual"] = 80.3
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            build_solidworks_runtime_evidence_from_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_CANONICAL_REPORT_MISMATCH",
        )

    def test_success_exit_requires_real_host_execution_flag(self) -> None:
        payload = successful_inputs()
        payload["real_host_executed"] = False
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            build_solidworks_runtime_evidence_from_inputs_v1(
                sketch_package=sketch_package(),
                runtime_inputs=payload,
            )
        self.assertEqual(
            captured.exception.code,
            "SOLIDWORKS_RUNTIME_REAL_HOST_REQUIRED",
        )

    def test_nonzero_exit_after_real_host_execution_is_failed(self) -> None:
        payload = successful_inputs()
        payload["agent_exit_code"] = 40
        payload["canonical_verification_report"] = None
        payload["bindings"] = []
        payload["read_back_dimensions"] = []
        payload["artifacts"] = []
        evidence = build_solidworks_runtime_evidence_from_inputs_v1(
            sketch_package=sketch_package(),
            runtime_inputs=payload,
        )
        self.assertEqual(evidence["status"], "FAILED")
        self.assertIn(
            "SOLIDWORKS_AGENT_EXIT_NONZERO",
            {item["code"] for item in evidence["diagnostics"]},
        )

    def test_nonzero_exit_before_real_host_execution_stays_unverified(self) -> None:
        payload = successful_inputs()
        payload["agent_exit_code"] = 30
        payload["real_host_executed"] = False
        payload["solidworks_version"] = None
        payload["canonical_verification_report"] = None
        payload["bindings"] = []
        payload["read_back_dimensions"] = []
        payload["artifacts"] = []
        evidence = build_solidworks_runtime_evidence_from_inputs_v1(
            sketch_package=sketch_package(),
            runtime_inputs=payload,
        )
        self.assertEqual(evidence["status"], "UNVERIFIED")

    def test_side_error_diagnostic_prevents_final_verified(self) -> None:
        payload = successful_inputs()
        payload["diagnostics"] = [
            {
                "code": "SIDE_POSTCHECK_FAILED",
                "stage": "HOST_RUNTIME",
                "message": "side post-check failed",
                "severity": "ERROR",
            }
        ]
        evidence = build_solidworks_runtime_evidence_from_inputs_v1(
            sketch_package=sketch_package(),
            runtime_inputs=payload,
        )
        self.assertEqual(evidence["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
