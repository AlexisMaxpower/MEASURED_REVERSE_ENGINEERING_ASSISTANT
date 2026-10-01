from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentConfig,
    build_solidworks_agent_request,
    build_solidworks_entity_rules_v1,
    evaluate_solidworks_entity_support_v1,
)


POINT = {
    "entity_id": "P-1",
    "type": "POINT",
    "point": {"x": 1.0, "y": 2.0},
}
LINE = {
    "entity_id": "L-1",
    "type": "LINE",
    "start": {"x": 0.0, "y": 0.0},
    "end": {"x": 10.0, "y": 0.0},
}
CIRCLE = {
    "entity_id": "C-1",
    "type": "CIRCLE",
    "center": {"x": 5.0, "y": 5.0},
    "radius": 2.0,
}
ARC = {
    "entity_id": "A-1",
    "type": "ARC",
    "center": {"x": 5.0, "y": 5.0},
    "radius": 2.0,
    "start_angle_deg": 0.0,
    "end_angle_deg": 90.0,
}


class SolidWorksEntityCapabilitiesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SolidWorksAgentConfig(
            executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
            output_directory=Path("C:/mrea/output"),
        )

    def package(self, *entities: dict) -> SimpleNamespace:
        return SimpleNamespace(
            sketch_package_id="SP-PASS14-ENTITY",
            expected_dimensions=(),
            dimensions=(),
            unresolved=(),
            entity_contracts=tuple(copy.deepcopy(entities)),
            constraints=(),
        )

    def test_rules_are_explicit_and_caller_safe(self) -> None:
        rules = build_solidworks_entity_rules_v1()
        self.assertEqual(rules["schema_version"], "mrea.solidworks-entity-rules.v1")
        self.assertEqual(set(rules["types"]), {"POINT", "LINE", "CIRCLE", "ARC"})
        self.assertEqual(rules["types"]["LINE"]["length_squared_mm2"]["exclusive_min"], 1e-24)
        self.assertEqual(rules["types"]["ARC"]["angles_deg"]["span_min_inclusive"], 1e-12)
        rules["types"]["LINE"]["required_points"].clear()
        fresh = build_solidworks_entity_rules_v1()
        self.assertEqual(fresh["types"]["LINE"]["required_points"], ["start", "end"])

    def test_supported_entities_pass_evaluator_and_request_preflight(self) -> None:
        for entity in (POINT, LINE, CIRCLE, ARC):
            with self.subTest(entity_type=entity["type"]):
                decision = evaluate_solidworks_entity_support_v1(entity)
                self.assertTrue(decision.supported, decision)

        request = build_solidworks_agent_request(
            self.package(POINT, LINE, CIRCLE, ARC),
            self.config,
        )
        self.assertEqual(
            [item["entity_id"] for item in request["entities"]],
            ["P-1", "L-1", "C-1", "A-1"],
        )

    def test_invalid_point_and_unsupported_type_fail_closed(self) -> None:
        invalid = copy.deepcopy(POINT)
        invalid["point"] = {"x": float("nan"), "y": 0.0}
        self.assertEqual(
            evaluate_solidworks_entity_support_v1(invalid).code,
            "POINT_INVALID",
        )

        unsupported = {"entity_id": "S-1", "type": "SPLINE"}
        self.assertEqual(
            evaluate_solidworks_entity_support_v1(unsupported).code,
            "TYPE_UNSUPPORTED",
        )

    def test_degenerate_line_fails_before_worker(self) -> None:
        line = copy.deepcopy(LINE)
        line["end"] = dict(line["start"])
        decision = evaluate_solidworks_entity_support_v1(line)
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "GEOMETRY_DEGENERATE")
        with self.assertRaises(CadAdapterError) as captured:
            build_solidworks_agent_request(self.package(line), self.config)
        self.assertIn("[GEOMETRY_DEGENERATE]", str(captured.exception))

    def test_radius_must_be_positive_and_finite(self) -> None:
        for source in (CIRCLE, ARC):
            for radius in (0.0, -1.0, float("inf")):
                entity = copy.deepcopy(source)
                entity["radius"] = radius
                with self.subTest(entity_type=entity["type"], radius=radius):
                    decision = evaluate_solidworks_entity_support_v1(entity)
                    self.assertFalse(decision.supported)
                    self.assertEqual(decision.code, "RADIUS_INVALID")

    def test_arc_zero_or_full_circle_span_fails_before_worker(self) -> None:
        for start, end in ((0.0, 0.0), (0.0, 360.0), (10.0, 370.0), (0.0, -360.0)):
            arc = copy.deepcopy(ARC)
            arc["start_angle_deg"] = start
            arc["end_angle_deg"] = end
            with self.subTest(start=start, end=end):
                decision = evaluate_solidworks_entity_support_v1(arc)
                self.assertFalse(decision.supported)
                self.assertEqual(decision.code, "GEOMETRY_DEGENERATE")
                with self.assertRaises(CadAdapterError):
                    build_solidworks_agent_request(self.package(arc), self.config)

    def test_duplicate_entity_ids_fail_before_worker(self) -> None:
        first = copy.deepcopy(LINE)
        second = copy.deepcopy(CIRCLE)
        second["entity_id"] = first["entity_id"]
        with self.assertRaises(CadAdapterError) as captured:
            build_solidworks_agent_request(self.package(first, second), self.config)
        self.assertIn("[ENTITY_ID_DUPLICATE]", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
