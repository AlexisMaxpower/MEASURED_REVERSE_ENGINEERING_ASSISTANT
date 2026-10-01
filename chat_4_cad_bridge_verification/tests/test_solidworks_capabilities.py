from __future__ import annotations

import unittest

from mrea_cad_bridge.solidworks_capabilities import (
    SOLIDWORKS_CAPABILITIES_SCHEMA,
    build_solidworks_capabilities_v1,
    is_solidworks_constraint_supported_v1,
)


class SolidWorksCapabilitiesTests(unittest.TestCase):
    def test_manifest_identity_is_stable(self):
        manifest = build_solidworks_capabilities_v1()
        self.assertEqual(manifest["schema_version"], SOLIDWORKS_CAPABILITIES_SCHEMA)
        self.assertEqual(manifest["adapter_name"], "SOLIDWORKS_2026")

    def test_complete_canonical_geometry_subset_is_declared_supported(self):
        manifest = build_solidworks_capabilities_v1()
        self.assertEqual(
            manifest["geometry_entities"]["supported"],
            ["POINT", "LINE", "CIRCLE", "ARC"],
        )

    def test_dimension_types_and_units_are_declared(self):
        manifest = build_solidworks_capabilities_v1()
        self.assertEqual(
            manifest["verified_dimensions"]["supported"],
            ["DISTANCE", "DIAMETER", "RADIUS", "ANGLE"],
        )
        self.assertEqual(manifest["verified_dimensions"]["units"]["ANGLE"], "deg")
        self.assertEqual(manifest["verified_dimensions"]["units"]["DISTANCE"], "mm")

    def test_current_supported_constraints_are_declared(self):
        manifest = build_solidworks_capabilities_v1()
        self.assertEqual(
            set(manifest["constraints"]["supported"]),
            {
                "HORIZONTAL",
                "VERTICAL",
                "PARALLEL",
                "PERPENDICULAR",
                "CONCENTRIC",
                "EQUAL",
                "TANGENT",
            },
        )

    def test_unimplemented_constraints_are_explicitly_unsupported(self):
        manifest = build_solidworks_capabilities_v1()
        self.assertEqual(
            set(manifest["constraints"]["unsupported"]),
            {"COINCIDENT", "SYMMETRIC"},
        )

    def test_tangent_is_reported_supported_after_worker_mapping_exists(self):
        self.assertTrue(is_solidworks_constraint_supported_v1("TANGENT"))

    def test_tangent_manifest_records_fail_closed_geometry_limit(self):
        manifest = build_solidworks_capabilities_v1()
        limitation = manifest["constraints"]["limitations"]["TANGENT"]
        self.assertIn("LINE/CIRCLE/ARC", limitation)
        self.assertIn("at least one CIRCLE/ARC", limitation)

    def test_nonverified_constraint_status_is_not_supported(self):
        self.assertFalse(
            is_solidworks_constraint_supported_v1("HORIZONTAL", status="DETECTED")
        )
        self.assertFalse(
            is_solidworks_constraint_supported_v1("TANGENT", status="INFERRED")
        )

    def test_verified_supported_constraint_is_reported_supported(self):
        self.assertTrue(is_solidworks_constraint_supported_v1("CONCENTRIC"))

    def test_manifest_does_not_claim_real_host_verified(self):
        manifest = build_solidworks_capabilities_v1()
        self.assertEqual(manifest["runtime"]["real_host_status"], "UNVERIFIED")
        self.assertEqual(manifest["runtime"]["production_build_status"], "UNVERIFIED")
        self.assertEqual(
            manifest["runtime"]["real_host_gate"], "EXTERNAL_EVIDENCE_REQUIRED"
        )

    def test_manifest_is_deep_copied_for_callers(self):
        first = build_solidworks_capabilities_v1()
        first["constraints"]["supported"].append("__MUTATED__")
        second = build_solidworks_capabilities_v1()
        self.assertNotIn("__MUTATED__", second["constraints"]["supported"])


if __name__ == "__main__":
    unittest.main()
