from __future__ import annotations

import copy
import unittest

from mrea_cad_bridge.runtime_receipt import (
    CadRuntimeReceiptError,
    RUNTIME_RECEIPT_SCHEMA,
    build_runtime_receipt_v1,
    canonical_json_bytes,
    sha256_json,
    verify_runtime_receipt_v1,
)

SKETCH = {
    "schema_version": "mrea.sketch-package.v1",
    "sketch_package_id": "SP-RECEIPT-001",
    "entities": [],
    "dimensions": [],
}
EVIDENCE = {
    "schema_version": "mrea.cad-runtime-evidence.v1",
    "sketch_package_id": "SP-RECEIPT-001",
    "adapter_name": "SOLIDWORKS_2026",
    "status": "VERIFIED",
}
CAD = {
    "schema_version": "mrea.cad-package.v1",
    "cad_package_id": "CAD-RECEIPT-001",
    "sketch_package_id": "SP-RECEIPT-001",
    "adapter": "SOLIDWORKS_2026",
    "artifacts": [
        {"artifact_id": "B", "kind": "SOLIDWORKS_PART", "uri": "file:///b.SLDPRT", "sha256": "b" * 64},
        {"artifact_id": "A", "kind": "SOLIDWORKS_PART", "uri": "file:///a.SLDPRT", "sha256": "a" * 64},
    ],
}
REPORT = {
    "schema_version": "mrea.cad-verification.v1",
    "report_id": "VR-RECEIPT-001",
    "sketch_package_id": "SP-RECEIPT-001",
    "cad_package_id": "CAD-RECEIPT-001",
    "overall_status": "VERIFIED",
    "items": [],
}
SOURCE = {"schema_version": "mrea.solidworks-runtime-inputs.v1", "agent_exit_code": 0}


def build(**overrides):
    values = dict(
        sketch_package=SKETCH,
        runtime_evidence=EVIDENCE,
        cad_package=CAD,
        cad_verification_report=REPORT,
        source_runtime_inputs=SOURCE,
    )
    values.update(overrides)
    return build_runtime_receipt_v1(**values)


class RuntimeReceiptTests(unittest.TestCase):
    def test_canonical_json_is_key_order_independent(self):
        self.assertEqual(sha256_json({"b": 2, "a": 1}), sha256_json({"a": 1, "b": 2}))

    def test_receipt_is_deterministic(self):
        self.assertEqual(build(), build())

    def test_receipt_binds_all_objects(self):
        receipt = build()
        self.assertEqual(receipt["schema_version"], RUNTIME_RECEIPT_SCHEMA)
        self.assertEqual(receipt["object_hashes"]["sketch_package_sha256"], sha256_json(SKETCH))
        self.assertEqual(receipt["object_hashes"]["runtime_evidence_sha256"], sha256_json(EVIDENCE))
        self.assertEqual(receipt["object_hashes"]["cad_package_sha256"], sha256_json(CAD))
        self.assertEqual(receipt["object_hashes"]["cad_verification_report_sha256"], sha256_json(REPORT))
        self.assertEqual(receipt["object_hashes"]["source_runtime_inputs_sha256"], sha256_json(SOURCE))

    def test_artifacts_are_normalized_by_id(self):
        self.assertEqual([x["artifact_id"] for x in build()["artifacts"]], ["A", "B"])

    def test_verify_accepts_untampered_receipt(self):
        verify_runtime_receipt_v1(
            receipt=build(),
            sketch_package=SKETCH,
            runtime_evidence=EVIDENCE,
            cad_package=CAD,
            cad_verification_report=REPORT,
            source_runtime_inputs=SOURCE,
        )

    def test_verify_detects_tampered_receipt(self):
        receipt = build()
        receipt["runtime_status"] = "FAILED"
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            verify_runtime_receipt_v1(
                receipt=receipt,
                sketch_package=SKETCH,
                runtime_evidence=EVIDENCE,
                cad_package=CAD,
                cad_verification_report=REPORT,
                source_runtime_inputs=SOURCE,
            )
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_SELF_HASH_MISMATCH")

    def test_verify_detects_source_object_tampering(self):
        receipt = build()
        changed = copy.deepcopy(EVIDENCE)
        changed["status"] = "FAILED"
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            verify_runtime_receipt_v1(
                receipt=receipt,
                sketch_package=SKETCH,
                runtime_evidence=changed,
                cad_package=CAD,
                cad_verification_report=REPORT,
                source_runtime_inputs=SOURCE,
            )
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_OBJECT_HASH_MISMATCH")

    def test_verified_requires_complete_chain(self):
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            build_runtime_receipt_v1(sketch_package=SKETCH, runtime_evidence=EVIDENCE)
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_VERIFIED_CHAIN_INCOMPLETE")

    def test_verified_requires_verified_canonical_report(self):
        report = copy.deepcopy(REPORT)
        report["overall_status"] = "FAILED"
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            build(cad_verification_report=report)
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_VERIFICATION_STATUS_MISMATCH")

    def test_cad_package_identity_mismatch_is_rejected(self):
        cad = copy.deepcopy(CAD)
        cad["sketch_package_id"] = "OTHER"
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            build(cad_package=cad)
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_CAD_SKETCH_ID_MISMATCH")

    def test_invalid_artifact_hash_is_rejected(self):
        cad = copy.deepcopy(CAD)
        cad["artifacts"][0]["sha256"] = "bad"
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            build(cad_package=cad)
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_ARTIFACT_HASH_INVALID")

    def test_non_finite_json_is_rejected(self):
        with self.assertRaises(CadRuntimeReceiptError) as captured:
            canonical_json_bytes({"x": float("nan")})
        self.assertEqual(captured.exception.code, "RUNTIME_RECEIPT_NON_CANONICAL_JSON")


if __name__ == "__main__":
    unittest.main()
