from __future__ import annotations

import unittest

from mrea_cad_bridge.runtime_evidence import (
    CadRuntimeEvidenceError,
    HostReadinessCheck,
    HostReadinessReport,
    ReadinessCheckStatus,
    RuntimeDiagnostic,
)
from mrea_cad_bridge.runtime_validation import execute_cad_runtime_validation_v1
from mrea_cad_bridge.test_double import TestDoubleCadAdapter
from mrea_cad_bridge.vendor import (
    CadAdapterResult,
    CadDimensionBinding,
    CadReadBack,
    CadReadBackDimension,
)


SKETCH_ID = "SP-PASS5-001"
ADAPTER = "SOLIDWORKS_2026"
SHA = "a" * 64


def sketch_package() -> dict:
    return {
        "schema_version": "mrea.sketch-package.v1",
        "sketch_package_id": SKETCH_ID,
        "project_id": "P-PASS5-001",
        "part_id": "PART-PASS5-001",
        "view_id": "VIEW-FRONT-PASS5-001",
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
        "source_view_ids": ["VIEW-FRONT-PASS5-001"],
    }


def ready_report(adapter_name: str = ADAPTER) -> HostReadinessReport:
    return HostReadinessReport(
        adapter_name=adapter_name,
        checks=(
            HostReadinessCheck(
                "OS_WINDOWS_11_X64",
                ReadinessCheckStatus.PASS,
                "Windows 11 x64 detected",
            ),
            HostReadinessCheck(
                "SOLIDWORKS_VERSION_2026",
                ReadinessCheckStatus.PASS,
                "SOLIDWORKS 2026 available",
            ),
            HostReadinessCheck(
                "OUTPUT_PATH_WRITABLE",
                ReadinessCheckStatus.PASS,
                "artifact output is writable",
            ),
        ),
    )


class CountingAdapter:
    adapter_name = ADAPTER

    def __init__(self, *, actual: float = 80.2, artifact: bool = True) -> None:
        self.calls = 0
        self.actual = actual
        self.artifact = artifact

    def transfer(self, package):
        self.calls += 1
        artifacts = ()
        if self.artifact:
            artifacts = (
                {
                    "artifact_id": "SWPART-PASS5-001",
                    "kind": "SOLIDWORKS_PART",
                    "uri": "file:///controlled/part.SLDPRT",
                    "media_type": "application/octet-stream",
                    "sha256": SHA,
                },
            )
        return CadAdapterResult(
            adapter_name=self.adapter_name,
            bindings=(
                CadDimensionBinding(
                    dimension_id="D-WIDTH",
                    measurement_id="M-WIDTH",
                    vendor_dimension_ref="D1@Sketch1",
                ),
            ),
            read_back=CadReadBack(
                dimensions=(
                    CadReadBackDimension(
                        dimension_id="D-WIDTH",
                        actual_value=self.actual,
                        unit="mm",
                    ),
                ),
            ),
            artifacts=artifacts,
        )


class RuntimeValidationTests(unittest.TestCase):
    def execute(self, adapter, **kwargs):
        return execute_cad_runtime_validation_v1(
            sketch_package=sketch_package(),
            adapter=adapter,
            cad_package_id="CAD-PASS5-001",
            report_id="VR-PASS5-001",
            **kwargs,
        )

    def test_generic_test_double_verifies_numerically_but_runtime_stays_unverified(self):
        result = self.execute(TestDoubleCadAdapter(), real_host_executed=False)
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.runtime_status, "UNVERIFIED")

    def test_missing_readiness_blocks_adapter_before_transfer(self):
        adapter = CountingAdapter()
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            self.execute(adapter, real_host_executed=True, solidworks_version="34.0")
        self.assertEqual(captured.exception.code, "HOST_READINESS_EVIDENCE_MISSING")
        self.assertEqual(adapter.calls, 0)

    def test_failed_readiness_blocks_adapter_before_transfer(self):
        adapter = CountingAdapter()
        readiness = HostReadinessReport(
            adapter_name=ADAPTER,
            checks=(HostReadinessCheck("OUTPUT_PATH_WRITABLE", ReadinessCheckStatus.FAIL, "no"),),
        )
        with self.assertRaises(CadRuntimeEvidenceError):
            self.execute(
                adapter,
                real_host_executed=True,
                host_readiness=readiness,
                solidworks_version="34.0",
            )
        self.assertEqual(adapter.calls, 0)

    def test_unverified_readiness_blocks_adapter_before_transfer(self):
        adapter = CountingAdapter()
        readiness = HostReadinessReport(
            adapter_name=ADAPTER,
            checks=(
                HostReadinessCheck(
                    "SOLIDWORKS_COM_REGISTERED",
                    ReadinessCheckStatus.UNVERIFIED,
                    "unknown",
                ),
            ),
        )
        with self.assertRaises(CadRuntimeEvidenceError):
            self.execute(
                adapter,
                real_host_executed=True,
                host_readiness=readiness,
                solidworks_version="34.0",
            )
        self.assertEqual(adapter.calls, 0)

    def test_readiness_adapter_mismatch_blocks_adapter_before_transfer(self):
        adapter = CountingAdapter()
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            self.execute(
                adapter,
                real_host_executed=True,
                host_readiness=ready_report("OTHER_ADAPTER"),
                solidworks_version="34.0",
            )
        self.assertEqual(captured.exception.code, "HOST_READINESS_ADAPTER_MISMATCH")
        self.assertEqual(adapter.calls, 0)

    def test_missing_version_blocks_adapter_before_transfer(self):
        adapter = CountingAdapter()
        with self.assertRaises(CadRuntimeEvidenceError) as captured:
            self.execute(
                adapter,
                real_host_executed=True,
                host_readiness=ready_report(),
                solidworks_version="  ",
            )
        self.assertEqual(captured.exception.code, "SOLIDWORKS_VERSION_MISSING")
        self.assertEqual(adapter.calls, 0)

    def test_complete_real_host_path_can_be_runtime_verified(self):
        adapter = CountingAdapter()
        result = self.execute(
            adapter,
            real_host_executed=True,
            host_readiness=ready_report(),
            solidworks_version="34.0",
        )
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.runtime_status, "VERIFIED")

    def test_numerical_mismatch_remains_runtime_failed(self):
        result = self.execute(
            CountingAdapter(actual=80.3),
            real_host_executed=True,
            host_readiness=ready_report(),
            solidworks_version="34.0",
        )
        self.assertEqual(result.verification_status, "FAILED")
        self.assertEqual(result.runtime_status, "FAILED")

    def test_missing_native_artifact_fails_runtime_evidence(self):
        result = self.execute(
            CountingAdapter(artifact=False),
            real_host_executed=True,
            host_readiness=ready_report(),
            solidworks_version="34.0",
        )
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.runtime_status, "FAILED")

    def test_runtime_error_diagnostic_forces_failed_evidence(self):
        result = self.execute(
            CountingAdapter(),
            real_host_executed=True,
            host_readiness=ready_report(),
            solidworks_version="34.0",
            diagnostics=(
                RuntimeDiagnostic(
                    code="HOST_POSTCHECK_FAILED",
                    stage="HOST_RUNTIME",
                    message="controlled host post-check failed",
                ),
            ),
        )
        self.assertEqual(result.verification_status, "VERIFIED")
        self.assertEqual(result.runtime_status, "FAILED")


if __name__ == "__main__":
    unittest.main()
