from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from mrea_cad_bridge import (
    ContractMappingError,
    VerificationEngine,
    build_cad_package_v1,
    build_cad_verification_report_v1,
    map_sketch_package_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "core" / "contracts"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator_for(definition: str) -> Draft202012Validator:
    schema = _load_json(CONTRACT_ROOT / "mrea_contracts_v1.schema.json")
    wrapper = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    return Draft202012Validator(wrapper)


class ContractBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sketch_package = _load_json(FIXTURE_ROOT / "sketch_package_v1.json")
        cls.expected_report = _load_json(FIXTURE_ROOT / "cad_verification_v1.json")
        cls.expected_cad_package = _load_json(FIXTURE_ROOT / "cad_package_v1.json")
        _validator_for("SketchPackage").validate(cls.sketch_package)
        _validator_for("CADVerificationReport").validate(cls.expected_report)
        _validator_for("CADPackage").validate(cls.expected_cad_package)

    def test_canonical_golden_sketch_maps_to_internal_cad_and_expected_dimensions(self) -> None:
        mapped = map_sketch_package_v1(self.sketch_package)
        self.assertEqual(mapped.sketch_package_id, "SP-GOLDEN-001")
        self.assertEqual(len(mapped.sketch.entities), 6)
        self.assertEqual(
            [item.dimension_id for item in mapped.expected_dimensions],
            ["D-WIDTH", "D-HEIGHT", "D-HOLE", "D-CENTER"],
        )
        self.assertTrue(all(item.tolerance == 1e-6 for item in mapped.expected_dimensions))

    def test_cad_package_builder_matches_canonical_fixture_exactly(self) -> None:
        canonical = build_cad_package_v1(
            cad_package_id=self.expected_cad_package["cad_package_id"],
            sketch_package_id=self.expected_cad_package["sketch_package_id"],
            adapter=self.expected_cad_package["adapter"],
            artifacts=self.expected_cad_package["artifacts"],
        )
        _validator_for("CADPackage").validate(canonical)
        self.assertEqual(canonical, self.expected_cad_package)

    def test_golden_verification_roundtrip_matches_canonical_fixture_exactly(self) -> None:
        mapped = map_sketch_package_v1(self.sketch_package)
        actual_values = {
            item["dimension_id"]: item["actual"]
            for item in self.expected_report["items"]
        }
        internal = VerificationEngine().verify(mapped.expected_dimensions, actual_values)
        canonical = build_cad_verification_report_v1(
            report_id=self.expected_report["report_id"],
            cad_package_id=self.expected_report["cad_package_id"],
            sketch_package_id=mapped.sketch_package_id,
            report=internal,
        )
        _validator_for("CADVerificationReport").validate(canonical)
        self.assertEqual(canonical, self.expected_report)

    def test_non_verified_dimension_is_not_cad_transfer_truth(self) -> None:
        package = copy.deepcopy(self.sketch_package)
        package["dimensions"][0]["verified"] = False
        mapped = map_sketch_package_v1(package)
        self.assertNotIn("D-WIDTH", [item.dimension_id for item in mapped.expected_dimensions])

    def test_unsupported_entity_is_rejected_instead_of_silently_dropped(self) -> None:
        package = copy.deepcopy(self.sketch_package)
        package["entities"].append(
            {
                "entity_id": "S-1",
                "type": "SPLINE",
                "provenance": "GEOMETRY_DERIVED",
            }
        )
        with self.assertRaises(ContractMappingError):
            map_sketch_package_v1(package)


if __name__ == "__main__":
    unittest.main()
