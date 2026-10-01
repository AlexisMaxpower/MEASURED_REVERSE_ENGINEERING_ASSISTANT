from __future__ import annotations

import json
from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentAdapter,
    SolidWorksAgentConfig,
    map_sketch_package_v1,
    parse_solidworks_agent_response,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


def _load_sketch_package() -> dict:
    return json.loads((FIXTURE_ROOT / "sketch_package_v1.json").read_text(encoding="utf-8"))


def _ok_response(sketch_package: dict) -> dict:
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
            "constraint_conflicts": [],
        },
        "artifacts": [
            {
                "artifact_id": f"SWPART-{sketch_package['sketch_package_id']}",
                "kind": "SOLIDWORKS_PART",
                "uri": f"file:///C:/mrea/{sketch_package['sketch_package_id']}.SLDPRT",
                "media_type": "application/octet-stream",
                "sha256": "pass16-test-sha256",
                "metadata": {
                    "adapter": "SOLIDWORKS_2026",
                    "solidworks_major": 2026,
                    "native_extension": ".SLDPRT",
                },
            }
        ],
    }


class FakeRunner:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.request = None

    def run(self, request):
        self.request = request
        return self.response


class SolidWorksSuccessResponseCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sketch_package = _load_sketch_package()
        cls.mapped = map_sketch_package_v1(cls.sketch_package)
        cls.dimension_ids = [
            item["dimension_id"]
            for item in cls.sketch_package["dimensions"]
            if item["verified"]
        ]

    def setUp(self) -> None:
        self.config = SolidWorksAgentConfig(
            executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
            output_directory=Path("C:/mrea/output"),
        )

    def transfer(self, response: dict):
        return SolidWorksAgentAdapter(
            self.config,
            runner=FakeRunner(response),
        ).transfer(self.mapped)

    def test_complete_success_response_is_accepted(self) -> None:
        result = self.transfer(_ok_response(self.sketch_package))
        self.assertEqual(
            {binding.dimension_id for binding in result.bindings},
            set(self.dimension_ids),
        )
        self.assertEqual(len(result.artifacts), 1)

    def test_missing_binding_fails_closed_even_when_response_claims_ok(self) -> None:
        response = _ok_response(self.sketch_package)
        missing_id = self.dimension_ids[0]
        response["bindings"] = [
            item for item in response["bindings"] if item["dimension_id"] != missing_id
        ]
        response["read_back"]["dimensions"] = [
            item
            for item in response["read_back"]["dimensions"]
            if item["dimension_id"] != missing_id
        ]

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("binding set does not match request", str(captured.exception))
        self.assertIn(missing_id, str(captured.exception))

    def test_unexpected_binding_fails_closed_even_when_internally_consistent(self) -> None:
        response = _ok_response(self.sketch_package)
        response["bindings"].append(
            {
                "dimension_id": "D-UNEXPECTED",
                "measurement_id": "M-UNEXPECTED",
                "vendor_dimension_ref": "MREA_D_UNEXPECTED@Sketch1@Part1.SLDPRT",
            }
        )
        response["read_back"]["dimensions"].append(
            {
                "dimension_id": "D-UNEXPECTED",
                "actual_value": 1.0,
                "unit": "mm",
            }
        )

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("binding set does not match request", str(captured.exception))
        self.assertIn("D-UNEXPECTED", str(captured.exception))

    def test_measurement_traceability_drift_fails_closed(self) -> None:
        response = _ok_response(self.sketch_package)
        response["bindings"][0]["measurement_id"] = "M-WRONG"

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("lost measurement traceability", str(captured.exception))

    def test_missing_read_back_or_conflict_evidence_fails_closed(self) -> None:
        response = _ok_response(self.sketch_package)
        missing_id = self.dimension_ids[0]
        response["read_back"]["dimensions"] = [
            item
            for item in response["read_back"]["dimensions"]
            if item["dimension_id"] != missing_id
        ]

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("omitted read-back/conflict evidence", str(captured.exception))
        self.assertIn(missing_id, str(captured.exception))

    def test_constraint_conflict_can_supply_evidence_without_numeric_read_back(self) -> None:
        response = _ok_response(self.sketch_package)
        conflict_id = self.dimension_ids[0]
        response["read_back"]["dimensions"] = [
            item
            for item in response["read_back"]["dimensions"]
            if item["dimension_id"] != conflict_id
        ]
        response["read_back"]["constraint_conflicts"] = [conflict_id]

        result = self.transfer(response)

        self.assertIn(conflict_id, result.read_back.constraint_conflicts)
        self.assertNotIn(conflict_id, result.read_back.actual_values())

    def test_read_back_unit_drift_fails_closed_at_vendor_boundary(self) -> None:
        response = _ok_response(self.sketch_package)
        response["read_back"]["dimensions"][0]["unit"] = "deg"

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("unit mismatch", str(captured.exception))

    def test_success_response_requires_native_solidworks_part_artifact(self) -> None:
        response = _ok_response(self.sketch_package)
        response["artifacts"] = []

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("exactly one SOLIDWORKS_PART artifact", str(captured.exception))

    def test_success_response_rejects_incomplete_native_artifact_metadata(self) -> None:
        response = _ok_response(self.sketch_package)
        response["artifacts"][0]["sha256"] = ""

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("incomplete native artifact metadata", str(captured.exception))
        self.assertIn("sha256", str(captured.exception))

    def test_cad_adapter_result_shape_errors_are_normalized_to_adapter_error(self) -> None:
        response = _ok_response(self.sketch_package)
        response["bindings"][1]["vendor_dimension_ref"] = response["bindings"][0][
            "vendor_dimension_ref"
        ]

        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)

        self.assertEqual(
            str(captured.exception),
            "invalid SOLIDWORKS CAD Agent response shape",
        )


if __name__ == "__main__":
    unittest.main()
