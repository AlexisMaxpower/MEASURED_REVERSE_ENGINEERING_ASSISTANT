from __future__ import annotations

import json
from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentAdapter,
    SolidWorksAgentConfig,
    execute_cad_transfer_v1,
    parse_solidworks_agent_response,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


def _load_sketch_package() -> dict:
    return json.loads((FIXTURE_ROOT / "sketch_package_v1.json").read_text(encoding="utf-8"))


def _ok_response(sketch_package: dict, *, conflicts=()) -> dict:
    dimensions = [item for item in sketch_package["dimensions"] if item["verified"]]
    return {
        "protocol_version": "mrea.solidworks-agent.v1",
        "status": "OK",
        "adapter_name": "SOLIDWORKS_2026",
        "bindings": [
            {
                "dimension_id": item["dimension_id"],
                "measurement_id": item.get("measurement_id"),
                "vendor_dimension_ref": f"MREA_{item['dimension_id']}@Sketch1@Part1.SLDPRT",
            }
            for item in dimensions
        ],
        "read_back": {
            "dimensions": [
                {
                    "dimension_id": item["dimension_id"],
                    "actual_value": item["value"],
                    "unit": item["unit"],
                }
                for item in dimensions
            ],
            "constraint_conflicts": list(conflicts),
        },
        "artifacts": [
            {
                "artifact_id": f"SWPART-{sketch_package['sketch_package_id']}",
                "kind": "SOLIDWORKS_PART",
                "uri": f"file:///C:/mrea/{sketch_package['sketch_package_id']}.SLDPRT",
                "media_type": "application/octet-stream",
                "sha256": "pass15-conflict-test-sha256",
                "metadata": {"adapter": "SOLIDWORKS_2026"},
            }
        ],
    }


class FakeRunner:
    def __init__(self, response: dict) -> None:
        self._response = response

    def run(self, request):
        return self._response


class SolidWorksConstraintConflictResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sketch_package = _load_sketch_package()
        cls.dimension_ids = [
            item["dimension_id"]
            for item in cls.sketch_package["dimensions"]
            if item["verified"]
        ]

    def test_agent_conflict_array_is_preserved_as_normalized_dimension_ids(self) -> None:
        response = _ok_response(
            self.sketch_package,
            conflicts=(self.dimension_ids[0],),
        )
        result = parse_solidworks_agent_response(response)
        self.assertEqual(
            result.read_back.constraint_conflicts,
            frozenset({self.dimension_ids[0]}),
        )

    def test_constraint_conflict_reaches_canonical_verification_report(self) -> None:
        conflict_id = self.dimension_ids[0]
        response = _ok_response(self.sketch_package, conflicts=(conflict_id,))
        adapter = SolidWorksAgentAdapter(
            SolidWorksAgentConfig(
                executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
                output_directory=Path("C:/mrea/output"),
            ),
            runner=FakeRunner(response),
        )
        execution = execute_cad_transfer_v1(
            sketch_package=self.sketch_package,
            adapter=adapter,
            cad_package_id="CAD-PASS15-CONFLICT",
            report_id="CAD-VERIFY-PASS15-CONFLICT",
        )
        item = {
            entry["dimension_id"]: entry
            for entry in execution.cad_verification_report["items"]
        }[conflict_id]
        self.assertEqual(item["status"], "CONSTRAINT_CONFLICT")
        self.assertIsNone(item["difference"])
        self.assertEqual(execution.cad_verification_report["overall_status"], "FAILED")

    def test_string_constraint_conflicts_is_rejected_instead_of_becoming_characters(self) -> None:
        response = _ok_response(self.sketch_package)
        response["read_back"]["constraint_conflicts"] = self.dimension_ids[0]
        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)
        self.assertIn("constraint_conflicts must be an array", str(captured.exception))

    def test_duplicate_constraint_conflict_dimension_id_is_rejected(self) -> None:
        conflict_id = self.dimension_ids[0]
        response = _ok_response(
            self.sketch_package,
            conflicts=(conflict_id, conflict_id),
        )
        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)
        self.assertIn("duplicate constraint conflict dimension_id", str(captured.exception))

    def test_unknown_constraint_conflict_dimension_id_is_rejected(self) -> None:
        response = _ok_response(
            self.sketch_package,
            conflicts=("D-NOT-BOUND",),
        )
        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)
        self.assertIn("unbound dimensions", str(captured.exception))

    def test_non_string_constraint_conflict_dimension_id_is_rejected(self) -> None:
        response = _ok_response(self.sketch_package)
        response["read_back"]["constraint_conflicts"] = [123]
        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)
        self.assertIn("non-empty strings", str(captured.exception))

    def test_non_object_read_back_is_rejected_consistently(self) -> None:
        response = _ok_response(self.sketch_package)
        response["read_back"] = []
        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)
        self.assertEqual(str(captured.exception), "invalid SOLIDWORKS CAD Agent response shape")


if __name__ == "__main__":
    unittest.main()
