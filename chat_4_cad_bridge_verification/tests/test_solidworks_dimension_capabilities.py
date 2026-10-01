from __future__ import annotations

import copy
from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentConfig,
    build_solidworks_agent_request,
    build_solidworks_dimension_rules_v1,
    evaluate_solidworks_dimension_support_v1,
    map_sketch_package_v1,
)


BASE = {
    "schema_version": "mrea.sketch-package.v1",
    "sketch_package_id": "SP-PASS13-DIMENSIONS",
    "project_id": "P-PASS13",
    "part_id": "PART-PASS13",
    "view_id": "VIEW-PASS13",
    "coordinate_system": "MAT_XY_MM",
    "entities": [
        {
            "entity_id": "L-H",
            "type": "LINE",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 50.0, "y": 0.0},
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "L-V",
            "type": "LINE",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 0.0, "y": 30.0},
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "L-PAR",
            "type": "LINE",
            "start": {"x": 0.0, "y": 10.0},
            "end": {"x": 50.0, "y": 10.0},
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "C-1",
            "type": "CIRCLE",
            "center": {"x": 10.0, "y": 10.0},
            "radius": 3.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "C-2",
            "type": "CIRCLE",
            "center": {"x": 30.0, "y": 10.0},
            "radius": 4.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "A-1",
            "type": "ARC",
            "center": {"x": 20.0, "y": 20.0},
            "radius": 5.0,
            "start_angle_deg": 0.0,
            "end_angle_deg": 90.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
    ],
    "constraints": [],
    "dimensions": [],
    "unresolved": [],
    "source_view_ids": ["VIEW-PASS13"],
}


def dimension(kind: str, entity_ids: list[str], *, unit: str | None = None, value: float = 10.0) -> dict:
    return {
        "dimension_id": "D-PASS13",
        "measurement_id": "M-PASS13",
        "type": kind,
        "value": value,
        "unit": unit or ("deg" if kind == "ANGLE" else "mm"),
        "entity_ids": entity_ids,
        "verified": True,
        "provenance": "MANUAL_MEASURED",
    }


class SolidWorksDimensionCapabilitiesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entities = {item["entity_id"]: item for item in BASE["entities"]}
        self.config = SolidWorksAgentConfig(
            executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
            output_directory=Path("C:/mrea/output"),
        )

    def decision(self, item: dict):
        return evaluate_solidworks_dimension_support_v1(item, self.entities)

    def request_for(self, item: dict) -> dict:
        package = copy.deepcopy(BASE)
        package["dimensions"] = [item]
        return build_solidworks_agent_request(map_sketch_package_v1(package), self.config)

    def test_rules_are_explicit_and_caller_safe(self) -> None:
        rules = build_solidworks_dimension_rules_v1()
        self.assertEqual(rules["schema_version"], "mrea.solidworks-dimension-rules.v1")
        self.assertTrue(rules["distinct_entity_ids"])
        self.assertEqual(
            rules["types"]["DISTANCE"]["entity_type_patterns"],
            [
                ["LINE"],
                ["CIRCLE", "CIRCLE"],
                ["CIRCLE", "ARC"],
                ["ARC", "CIRCLE"],
                ["ARC", "ARC"],
            ],
        )
        rules["types"]["RADIUS"]["entity_type_patterns"].clear()
        fresh = build_solidworks_dimension_rules_v1()
        self.assertEqual(fresh["types"]["RADIUS"]["entity_type_patterns"], [["CIRCLE"], ["ARC"]])

    def test_supported_dimension_patterns_pass_preflight(self) -> None:
        supported = [
            dimension("DISTANCE", ["L-H"], value=50.0),
            dimension("DISTANCE", ["C-1", "C-2"], value=20.0),
            dimension("DISTANCE", ["C-1", "A-1"], value=14.1421356),
            dimension("DISTANCE", ["A-1", "C-2"], value=14.1421356),
            dimension("DISTANCE", ["A-1", "C-1"], value=14.1421356),
            dimension("DIAMETER", ["C-1"], value=6.0),
            dimension("RADIUS", ["C-1"], value=3.0),
            dimension("RADIUS", ["A-1"], value=5.0),
            dimension("ANGLE", ["L-H", "L-V"], value=90.0),
        ]
        for item in supported:
            with self.subTest(kind=item["type"], entity_ids=item["entity_ids"]):
                decision = self.decision(item)
                self.assertTrue(decision.supported, decision)
                request = self.request_for(item)
                self.assertEqual(request["dimensions"][0]["entity_ids"], item["entity_ids"])

    def test_unsupported_entity_patterns_fail_closed_before_worker(self) -> None:
        cases = [
            (dimension("DISTANCE", ["C-1"]), "ENTITY_PATTERN_UNSUPPORTED"),
            (dimension("DISTANCE", ["L-H", "L-V"]), "ENTITY_PATTERN_UNSUPPORTED"),
            (dimension("DIAMETER", ["A-1"]), "ENTITY_PATTERN_UNSUPPORTED"),
            (dimension("DIAMETER", ["L-H"]), "ENTITY_PATTERN_UNSUPPORTED"),
            (dimension("RADIUS", ["L-H"]), "ENTITY_PATTERN_UNSUPPORTED"),
            (dimension("ANGLE", ["L-H", "C-1"], value=45.0), "ENTITY_PATTERN_UNSUPPORTED"),
        ]
        for item, code in cases:
            with self.subTest(kind=item["type"], entity_ids=item["entity_ids"]):
                decision = self.decision(item)
                self.assertFalse(decision.supported)
                self.assertEqual(decision.code, code)
                with self.assertRaises(CadAdapterError) as captured:
                    self.request_for(item)
                self.assertIn(f"[{code}]", str(captured.exception))

    def test_duplicate_and_unknown_entity_ids_fail_closed(self) -> None:
        duplicate = dimension("DISTANCE", ["C-1", "C-1"], value=0.0)
        self.assertEqual(self.decision(duplicate).code, "ENTITY_IDS_DUPLICATE")
        with self.assertRaises(CadAdapterError):
            self.request_for(duplicate)

        unknown = dimension("RADIUS", ["A-MISSING"], value=5.0)
        self.assertEqual(self.decision(unknown).code, "ENTITY_UNKNOWN")
        with self.assertRaises(CadAdapterError):
            self.request_for(unknown)

    def test_units_are_type_specific(self) -> None:
        wrong_linear = dimension("RADIUS", ["A-1"], unit="deg", value=5.0)
        self.assertEqual(self.decision(wrong_linear).code, "UNIT_UNSUPPORTED")
        with self.assertRaises(CadAdapterError):
            self.request_for(wrong_linear)

        wrong_angle = dimension("ANGLE", ["L-H", "L-V"], unit="mm", value=90.0)
        self.assertEqual(self.decision(wrong_angle).code, "UNIT_UNSUPPORTED")
        with self.assertRaises(CadAdapterError):
            self.request_for(wrong_angle)

    def test_angle_range_and_parallel_geometry_fail_closed(self) -> None:
        for value in (0.0, 180.0):
            item = dimension("ANGLE", ["L-H", "L-V"], value=value)
            with self.subTest(value=value):
                self.assertEqual(self.decision(item).code, "VALUE_OUT_OF_RANGE")
                with self.assertRaises(CadAdapterError):
                    self.request_for(item)

        parallel = dimension("ANGLE", ["L-H", "L-PAR"], value=45.0)
        self.assertEqual(self.decision(parallel).code, "GEOMETRY_UNSUPPORTED")
        with self.assertRaises(CadAdapterError) as captured:
            self.request_for(parallel)
        self.assertIn("[GEOMETRY_UNSUPPORTED]", str(captured.exception))

    def test_degenerate_angle_line_is_invalid_geometry(self) -> None:
        entities = copy.deepcopy(self.entities)
        entities["L-V"]["end"] = dict(entities["L-V"]["start"])
        item = dimension("ANGLE", ["L-H", "L-V"], value=90.0)
        decision = evaluate_solidworks_dimension_support_v1(item, entities)
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "GEOMETRY_INVALID")


if __name__ == "__main__":
    unittest.main()
