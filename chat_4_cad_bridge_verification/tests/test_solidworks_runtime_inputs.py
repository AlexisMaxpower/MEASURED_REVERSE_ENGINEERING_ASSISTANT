from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_solidworks_host_validation.py"
SPEC = importlib.util.spec_from_file_location("mrea_sw_host_validation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SolidWorksRuntimeInputsTests(unittest.TestCase):
    def _ready_report(self) -> dict:
        checks = [
            {
                "code": code,
                "status": "PASS",
                "message": "ok",
                "required": True,
            }
            for code in sorted(MODULE.REQUIRED_READINESS_CODES)
        ]
        checks.append(
            {
                "code": "OPTIONAL_NOTE",
                "status": "UNVERIFIED",
                "message": "optional",
                "required": False,
            }
        )
        return {
            "schema_version": MODULE.HOST_READINESS_SCHEMA,
            "adapter_name": MODULE.ADAPTER_NAME,
            "status": "READY",
            "checks": checks,
        }

    def test_recomputes_ready_instead_of_trusting_reported_status(self) -> None:
        report = self._ready_report()
        report["checks"][0]["status"] = "UNVERIFIED"
        with self.assertRaises(ValueError):
            MODULE.recompute_host_readiness(report)

    def test_missing_required_readiness_code_is_rejected(self) -> None:
        report = self._ready_report()
        report["checks"] = [
            item
            for item in report["checks"]
            if item["code"] != "SOLIDWORKS_COM_REGISTERED"
        ]
        with self.assertRaises(ValueError):
            MODULE.recompute_host_readiness(report)

    def test_runtime_inputs_are_not_final_runtime_evidence(self) -> None:
        bundle = MODULE.build_runtime_inputs(
            host_readiness=self._ready_report(),
            request={
                "adapter_name": MODULE.ADAPTER_NAME,
                "sketch_package_id": "SKETCH-001",
            },
            agent_exit_code=0,
            agent_response={
                "adapter_name": MODULE.ADAPTER_NAME,
                "real_host_executed": True,
                "solidworks_version": "34.0.0",
                "bindings": [],
                "read_back": {"dimensions": [], "constraint_conflicts": []},
                "artifacts": [],
                "diagnostics": [],
            },
            canonical_verification_report={"overall_status": "VERIFIED"},
        )
        self.assertEqual(bundle["schema_version"], MODULE.RUNTIME_INPUTS_SCHEMA)
        self.assertNotEqual(bundle["schema_version"], "mrea.cad-runtime-evidence.v1")
        self.assertNotIn("status", bundle)
        self.assertTrue(bundle["real_host_executed"])
        self.assertEqual(bundle["solidworks_version"], "34.0.0")
        self.assertEqual(bundle["sketch_package_id"], "SKETCH-001")

    def test_native_artifact_hash_is_rechecked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "part.SLDPRT"
            path.write_bytes(b"native-part")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            diagnostics = MODULE.verify_native_artifacts(
                [
                    {
                        "kind": "SOLIDWORKS_PART",
                        "uri": path.resolve().as_uri(),
                        "sha256": expected,
                    }
                ]
            )
            self.assertEqual(diagnostics, [])

    def test_native_artifact_hash_mismatch_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "part.SLDPRT"
            path.write_bytes(b"native-part")
            diagnostics = MODULE.verify_native_artifacts(
                [
                    {
                        "kind": "SOLIDWORKS_PART",
                        "uri": path.resolve().as_uri(),
                        "sha256": "0" * 64,
                    }
                ]
            )
            self.assertEqual(diagnostics[0]["code"], "ARTIFACT_SHA256_MISMATCH")
            self.assertEqual(diagnostics[0]["stage"], "ARTIFACT")


if __name__ == "__main__":
    unittest.main()
