from __future__ import annotations

import json
from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    CadAdapterResult,
    CadDimensionBinding,
    CadReadBack,
    CadReadBackDimension,
    TestDoubleCadAdapter,
    execute_cad_transfer_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class AdapterPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sketch_package = _load_json("sketch_package_v1.json")
        cls.expected_cad_package = _load_json("cad_package_v1.json")
        cls.expected_report = _load_json("cad_verification_v1.json")

    def execute(self, adapter) -> object:
        return execute_cad_transfer_v1(
            sketch_package=self.sketch_package,
            adapter=adapter,
            cad_package_id=self.expected_cad_package["cad_package_id"],
            report_id=self.expected_report["report_id"],
        )

    def test_test_double_golden_flow_matches_both_canonical_outputs_exactly(self) -> None:
        result = self.execute(TestDoubleCadAdapter())

        self.assertEqual(result.cad_package, self.expected_cad_package)
        self.assertEqual(
            result.cad_verification_report,
            self.expected_report,
        )
        self.assertEqual(
            [binding.dimension_id for binding in result.adapter_result.bindings],
            ["D-WIDTH", "D-HEIGHT", "D-HOLE", "D-CENTER"],
        )
        self.assertEqual(
            [binding.measurement_id for binding in result.adapter_result.bindings],
            ["M-WIDTH", "M-HEIGHT", "M-HOLE", "M-CENTER"],
        )
        self.assertEqual(
            [binding.vendor_dimension_ref for binding in result.adapter_result.bindings],
            [
                "TEST_DOUBLE::DIM::D-WIDTH",
                "TEST_DOUBLE::DIM::D-HEIGHT",
                "TEST_DOUBLE::DIM::D-HOLE",
                "TEST_DOUBLE::DIM::D-CENTER",
            ],
        )

    def test_test_double_mismatch_preserves_expected_and_actual(self) -> None:
        result = self.execute(
            TestDoubleCadAdapter(actual_overrides={"D-HOLE": 5.31})
        )
        item = {
            entry["dimension_id"]: entry
            for entry in result.cad_verification_report["items"]
        }["D-HOLE"]

        self.assertEqual(item["status"], "MISMATCH")
        self.assertEqual(item["expected"], 5.1)
        self.assertEqual(item["actual"], 5.31)
        self.assertEqual(result.cad_verification_report["overall_status"], "FAILED")

    def test_test_double_missing_readback_becomes_missing(self) -> None:
        result = self.execute(
            TestDoubleCadAdapter(
                missing_readback_ids=frozenset({"D-CENTER"})
            )
        )
        item = {
            entry["dimension_id"]: entry
            for entry in result.cad_verification_report["items"]
        }["D-CENTER"]

        self.assertEqual(item["status"], "MISSING")
        self.assertIsNone(item["actual"])
        self.assertIsNone(item["difference"])

    def test_constraint_conflict_is_forwarded_to_verification(self) -> None:
        result = self.execute(
            TestDoubleCadAdapter(
                constraint_conflicts=frozenset({"D-WIDTH"})
            )
        )
        self.assertEqual(
            result.cad_verification_report["items"][0]["status"],
            "CONSTRAINT_CONFLICT",
        )

    def test_unknown_test_double_control_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.execute(
                TestDoubleCadAdapter(actual_overrides={"D-NOT-REAL": 1.0})
            )

    def test_unit_mismatch_is_rejected_before_numeric_comparison(self) -> None:
        class BadUnitAdapter:
            adapter_name = "BAD_UNIT"

            def transfer(self, package):
                bindings = tuple(
                    CadDimensionBinding(
                        dimension_id=item.dimension_id,
                        measurement_id=item.measurement_id,
                        vendor_dimension_ref=f"BAD::{item.dimension_id}",
                    )
                    for item in package.expected_dimensions
                )
                first = package.expected_dimensions[0]
                return CadAdapterResult(
                    adapter_name=self.adapter_name,
                    bindings=bindings,
                    read_back=CadReadBack(
                        dimensions=(
                            CadReadBackDimension(
                                dimension_id=first.dimension_id,
                                actual_value=first.expected_value,
                                unit="deg",
                            ),
                        )
                    ),
                )

        with self.assertRaises(CadAdapterError):
            self.execute(BadUnitAdapter())


if __name__ == "__main__":
    unittest.main()
