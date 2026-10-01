from __future__ import annotations

import unittest

from mrea_cad_bridge import (
    build_solidworks_capabilities_v1,
    evaluate_solidworks_constraint_support_v1,
)


ENTITIES = {
    "L1": {"entity_id": "L1", "type": "LINE"},
    "L2": {"entity_id": "L2", "type": "LINE"},
    "C1": {"entity_id": "C1", "type": "CIRCLE"},
    "A1": {"entity_id": "A1", "type": "ARC"},
    "P1": {"entity_id": "P1", "type": "POINT"},
}


def constraint(kind, entity_ids, *, status="VERIFIED", constraint_id="K1"):
    return {
        "constraint_id": constraint_id,
        "type": kind,
        "entity_ids": entity_ids,
        "status": status,
    }


class SolidWorksConstraintCapabilityTests(unittest.TestCase):
    def evaluate(self, item):
        return evaluate_solidworks_constraint_support_v1(item, ENTITIES)

    def test_rules_are_explicit_machine_readable_and_caller_safe(self):
        manifest = build_solidworks_capabilities_v1()
        rules = manifest["constraints"]["rules"]
        self.assertTrue(rules["constraint_id_required"])
        self.assertTrue(rules["distinct_entity_ids"])
        self.assertTrue(rules["references_must_exist"])
        self.assertEqual(
            rules["types"]["HORIZONTAL"]["entity_type_patterns"],
            [["LINE"]],
        )
        self.assertEqual(
            rules["types"]["EQUAL"]["entity_type_patterns"],
            [["LINE", "LINE"]],
        )
        self.assertNotIn(
            ["LINE", "LINE"],
            rules["types"]["TANGENT"]["entity_type_patterns"],
        )
        rules["types"]["TANGENT"]["entity_type_patterns"].clear()
        fresh = build_solidworks_capabilities_v1()
        self.assertTrue(fresh["constraints"]["rules"]["types"]["TANGENT"]["entity_type_patterns"])

    def test_verified_tangent_line_circle_is_supported(self):
        decision = self.evaluate(constraint("TANGENT", ["L1", "C1"]))
        self.assertTrue(decision.supported)
        self.assertEqual(decision.code, "SUPPORTED")
        self.assertEqual(decision.entity_types, ("LINE", "CIRCLE"))

    def test_verified_tangent_circle_arc_is_supported(self):
        decision = self.evaluate(constraint("TANGENT", ["C1", "A1"]))
        self.assertTrue(decision.supported)
        self.assertEqual(decision.code, "SUPPORTED")
        self.assertEqual(decision.entity_types, ("CIRCLE", "ARC"))

    def test_missing_constraint_id_is_rejected_before_worker(self):
        item = constraint("HORIZONTAL", ["L1"])
        item["constraint_id"] = ""
        decision = self.evaluate(item)
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "CONSTRAINT_ID_INVALID")

    def test_nonverified_status_has_machine_readable_reason(self):
        decision = self.evaluate(
            constraint("TANGENT", ["L1", "C1"], status="INFERRED")
        )
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "STATUS_NOT_VERIFIED")
        self.assertEqual(decision.status, "INFERRED")

    def test_unsupported_constraint_type_has_machine_readable_reason(self):
        decision = self.evaluate(constraint("COINCIDENT", ["L1", "L2"]))
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "TYPE_UNSUPPORTED")
        self.assertEqual(decision.constraint_type, "COINCIDENT")

    def test_duplicate_entity_ids_are_rejected_before_geometry_rules(self):
        decision = self.evaluate(constraint("TANGENT", ["C1", "C1"]))
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "ENTITY_IDS_DUPLICATE")

    def test_unknown_entity_is_reported_explicitly(self):
        decision = self.evaluate(constraint("TANGENT", ["L1", "MISSING"]))
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "ENTITY_UNKNOWN")
        self.assertIn("MISSING", decision.message)

    def test_tangent_wrong_arity_is_distinguished_from_geometry(self):
        decision = self.evaluate(constraint("TANGENT", ["C1"]))
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "ARITY_UNSUPPORTED")

    def test_tangent_line_line_is_geometry_unsupported(self):
        decision = self.evaluate(constraint("TANGENT", ["L1", "L2"]))
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "GEOMETRY_UNSUPPORTED")
        self.assertEqual(decision.entity_types, ("LINE", "LINE"))

    def test_tangent_point_participation_is_geometry_unsupported(self):
        decision = self.evaluate(constraint("TANGENT", ["P1", "C1"]))
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "GEOMETRY_UNSUPPORTED")
        self.assertEqual(decision.entity_types, ("POINT", "CIRCLE"))

    def test_existing_relation_rules_use_same_evaluator(self):
        horizontal = self.evaluate(constraint("HORIZONTAL", ["L1"]))
        concentric = self.evaluate(constraint("CONCENTRIC", ["C1", "A1"]))
        bad_equal = self.evaluate(constraint("EQUAL", ["L1", "C1"]))

        self.assertTrue(horizontal.supported)
        self.assertTrue(concentric.supported)
        self.assertFalse(bad_equal.supported)
        self.assertEqual(bad_equal.code, "GEOMETRY_UNSUPPORTED")

    def test_entity_ids_shape_is_fail_closed(self):
        item = constraint("TANGENT", ["L1", "C1"])
        item["entity_ids"] = "L1,C1"
        decision = self.evaluate(item)
        self.assertFalse(decision.supported)
        self.assertEqual(decision.code, "ENTITY_IDS_INVALID")


if __name__ == "__main__":
    unittest.main()
