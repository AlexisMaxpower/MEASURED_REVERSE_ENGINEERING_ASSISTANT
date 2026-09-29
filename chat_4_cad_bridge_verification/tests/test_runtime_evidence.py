from __future__ import annotations

import unittest
from types import SimpleNamespace

from mrea_cad_bridge.runtime_evidence import (
    CadRuntimeEvidenceError,
    HostReadinessCheck,
    HostReadinessReport,
    HostReadinessStatus,
    ReadinessCheckStatus,
    RuntimeEvidenceStatus,
    build_runtime_evidence,
    parse_host_readiness_report,
    parse_runtime_diagnostic,
    require_host_ready,
)
from mrea_cad_bridge.vendor import (
    CadAdapterResult,
    CadDimensionBinding,
    CadReadBack,
    CadReadBackDimension,
)


ADAPTER = "SOLIDWORKS_2026"
SKETCH = "SP-GOLDEN-001"
SHA = "a" * 64


def ready_report() -> HostReadinessReport:
    return HostReadinessReport(
        adapter_name=ADAPTER,
        checks=(
            HostReadinessCheck("OS_WINDOWS_11", ReadinessCheckStatus.PASS, "Windows 11 x64 detected"),
            HostReadinessCheck("SOLIDWORKS_2026", ReadinessCheckStatus.PASS, "SOLIDWORKS 2026 detected"),
        ),
    )


def fake_execution(*, overall_status: str = "VERIFIED", artifact_sha: str | None = SHA):
    read_back = CadReadBack(
        dimensions=(CadReadBackDimension("D-WIDTH", 80.2, "mm"),),
    )
    artifact = {
        "artifact_id": "SWPART-1",
        "kind": "SOLIDWORKS_PART",
        "uri": "file:///tmp/part.SLDPRT",
        "sha256": artifact_sha,
    }
    result = CadAdapterResult(
        adapter_name=ADAPTER,
        bindings=(CadDimensionBinding("D-WIDTH", "M-WIDTH", "D1@Sketch1"),),
        read_back=read_back,
        artifacts=(artifact,),
    )
    report_item = {
        "dimension_id": "D-WIDTH",
        "measurement_id": "M-WIDTH",
        "expected": 80.2,
        "actual": 80.2 if overall_status == "VERIFIED" else 80.3,
        "unit": "mm",
        "tolerance": 1e-6,
        "difference": 0.0 if overall_status == "VERIFIED" else 0.1,
        "status": "VERIFIED" if overall_status == "VERIFIED" else "MISMATCH",
    }
    return SimpleNamespace(
        mapped_sketch_package=SimpleNamespace(sketch_package_id=SKETCH),
        adapter_result=result,
        cad_package={
            "schema_version": "mrea.cad-package.v1",
            "cad_package_id": "CAD-1",
            "sketch_package_id": SKETCH,
            "adapter": ADAPTER,
            "artifacts": [artifact],
        },
        cad_verification_report={
            "schema_version": "mrea.cad-verification.v1",
            "report_id": "VR-1",
            "cad_package_id": "CAD-1",
            "sketch_package_id": SKETCH,
            "items": [report_item],
            "overall_status": overall_status,
        },
    )


class HostReadinessTests(unittest.TestCase):
    def test_ready_when_all_required_checks_pass(self):
        self.assertIs(ready_report().status, HostReadinessStatus.READY)

    def test_fail_takes_precedence_over_unverified(self):
        report = HostReadinessReport(
            adapter_name=ADAPTER,
            checks=(
                HostReadinessCheck("A", ReadinessCheckStatus.UNVERIFIED, "unknown"),
                HostReadinessCheck("B", ReadinessCheckStatus.FAIL, "failed"),
            ),
        )
        self.assertIs(report.status, HostReadinessStatus.FAILED)

    def test_require_host_ready_exposes_machine_readable_code(self):
        report = HostReadinessReport(
            adapter_name=ADAPTER,
            checks=(HostReadinessCheck("OUTPUT_PATH_WRITABLE", ReadinessCheckStatus.FAIL, "not writable"),),
        )
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            require_host_ready(report)
        self.assertEqual(captured.exception.code, "OUTPUT_PATH_WRITABLE")
        self.assertEqual(captured.exception.stage, "HOST_PREFLIGHT")

    def test_readiness_parser_recomputes_status(self):
        payload = ready_report().to_dict()
        parsed = parse_host_readiness_report(payload)
        self.assertIs(parsed.status, HostReadinessStatus.READY)

    def test_readiness_parser_rejects_claimed_ready_when_check_failed(self):
        payload = {
            "schema_version": "mrea.cad-host-readiness.v1",
            "adapter_name": ADAPTER,
            "status": "READY",
            "checks": [
                {
                    "code": "SOLIDWORKS_2026",
                    "status": "FAIL",
                    "message": "wrong version",
                    "required": True,
                }
            ],
        }
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            parse_host_readiness_report(payload)
        self.assertEqual(captured.exception.code, "HOST_READINESS_STATUS_MISMATCH")

    def test_runtime_diagnostic_parser_is_strict(self):
        diagnostic = parse_runtime_diagnostic({
            "code": "SOLIDWORKS_COM_NOT_REGISTERED",
            "stage": "HOST_PREFLIGHT",
            "message": "COM ProgID missing",
            "severity": "ERROR",
            "details": {"prog_id": "SldWorks.Application"},
        })
        self.assertEqual(diagnostic.code, "SOLIDWORKS_COM_NOT_REGISTERED")
        self.assertEqual(diagnostic.details["prog_id"], "SldWorks.Application")


class RuntimeEvidenceTests(unittest.TestCase):
    def test_numerical_verification_without_real_host_stays_unverified(self):
        evidence = build_runtime_evidence(
            sketch_package_id=SKETCH,
            adapter_name=ADAPTER,
            real_host_executed=False,
            execution=fake_execution(),
        )
        self.assertEqual(evidence["status"], RuntimeEvidenceStatus.UNVERIFIED.value)
        self.assertIn("REAL_HOST_NOT_EXECUTED", {d["code"] for d in evidence["diagnostics"]})

    def test_real_host_without_version_fails_closed(self):
        evidence = build_runtime_evidence(
            sketch_package_id=SKETCH,
            adapter_name=ADAPTER,
            real_host_executed=True,
            execution=fake_execution(),
            host_readiness=ready_report(),
        )
        self.assertEqual(evidence["status"], RuntimeEvidenceStatus.FAILED.value)
        self.assertIn("SOLIDWORKS_VERSION_MISSING", {d["code"] for d in evidence["diagnostics"]})

    def test_real_host_without_hashed_native_artifact_fails_closed(self):
        evidence = build_runtime_evidence(
            sketch_package_id=SKETCH,
            adapter_name=ADAPTER,
            real_host_executed=True,
            execution=fake_execution(artifact_sha=None),
            host_readiness=ready_report(),
            solidworks_version="34.0",
        )
        self.assertEqual(evidence["status"], RuntimeEvidenceStatus.FAILED.value)
        self.assertIn("NATIVE_ARTIFACT_EVIDENCE_MISSING", {d["code"] for d in evidence["diagnostics"]})

    def test_full_real_host_evidence_can_be_verified(self):
        evidence = build_runtime_evidence(
            sketch_package_id=SKETCH,
            adapter_name=ADAPTER,
            real_host_executed=True,
            execution=fake_execution(),
            host_readiness=ready_report(),
            solidworks_version="34.0",
        )
        self.assertEqual(evidence["status"], RuntimeEvidenceStatus.VERIFIED.value)
        self.assertEqual(evidence["artifacts"][0]["sha256"], SHA)
        self.assertEqual(evidence["read_back_dimensions"][0]["dimension_id"], "D-WIDTH")

    def test_failed_numerical_verification_remains_failed(self):
        execution = fake_execution(overall_status="FAILED")
        execution.adapter_result = CadAdapterResult(
            adapter_name=ADAPTER,
            bindings=(CadDimensionBinding("D-WIDTH", "M-WIDTH", "D1@Sketch1"),),
            read_back=CadReadBack(
                dimensions=(CadReadBackDimension("D-WIDTH", 80.3, "mm"),),
            ),
            artifacts=tuple(execution.cad_package["artifacts"]),
        )
        evidence = build_runtime_evidence(
            sketch_package_id=SKETCH,
            adapter_name=ADAPTER,
            real_host_executed=True,
            execution=execution,
            host_readiness=ready_report(),
            solidworks_version="34.0",
        )
        self.assertEqual(evidence["status"], RuntimeEvidenceStatus.FAILED.value)

    def test_sketch_identity_mismatch_is_rejected(self):
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            build_runtime_evidence(
                sketch_package_id="SP-OTHER",
                adapter_name=ADAPTER,
                real_host_executed=False,
                execution=fake_execution(),
            )
        self.assertEqual(captured.exception.code, "SKETCH_PACKAGE_ID_MISMATCH")

    def test_read_back_report_drift_is_rejected(self):
        execution = fake_execution()
        execution.adapter_result = CadAdapterResult(
            adapter_name=ADAPTER,
            bindings=(CadDimensionBinding("D-WIDTH", "M-WIDTH", "D1@Sketch1"),),
            read_back=CadReadBack(
                dimensions=(CadReadBackDimension("D-WIDTH", 80.25, "mm"),),
            ),
            artifacts=tuple(execution.cad_package["artifacts"]),
        )
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            build_runtime_evidence(
                sketch_package_id=SKETCH,
                adapter_name=ADAPTER,
                real_host_executed=True,
                execution=execution,
                host_readiness=ready_report(),
                solidworks_version="34.0",
            )
        self.assertEqual(captured.exception.code, "READ_BACK_EVIDENCE_MISMATCH")

    def test_artifact_drift_between_adapter_and_cad_package_is_rejected(self):
        execution = fake_execution()
        execution.cad_package = dict(execution.cad_package)
        execution.cad_package["artifacts"] = [dict(execution.cad_package["artifacts"][0], sha256="b" * 64)]
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            build_runtime_evidence(
                sketch_package_id=SKETCH,
                adapter_name=ADAPTER,
                real_host_executed=True,
                execution=execution,
                host_readiness=ready_report(),
                solidworks_version="34.0",
            )
        self.assertEqual(captured.exception.code, "ARTIFACT_EVIDENCE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
