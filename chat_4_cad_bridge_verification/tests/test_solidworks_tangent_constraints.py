from __future__ import annotations

from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentConfig,
    build_solidworks_agent_request,
    map_sketch_package_v1,
)


BASE_PACKAGE = {
    "schema_version": "mrea.sketch-package.v1",
    "sketch_package_id": "SP-TANGENT-001",
    "project_id": "P-TANGENT-001",
    "part_id": "PART-TANGENT-001",
    "view_id": "VIEW-TANGENT-001",
    "coordinate_system": "MAT_XY_MM",
    "entities": [
        {
            "entity_id": "L1",
            "type": "LINE",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 20.0, "y": 0.0},
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "L2",
            "type": "LINE",
            "start": {"x": 0.0, "y": 10.0},
            "end": {"x": 20.0, "y": 10.0},
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "C1",
            "type": "CIRCLE",
            "center": {"x": 10.0, "y": 5.0},
            "radius": 5.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "C2",
            "type": "CIRCLE",
            "center": {"x": 20.0, "y": 5.0},
            "radius": 5.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "A1",
            "type": "ARC",
            "center": {"x": 10.0, "y": 5.0},
            "radius": 5.0,
            "start_angle_deg": 0.0,
            "end_angle_deg": 90.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "A2",
            "type": "ARC",
            "center": {"x": 20.0, "y": 5.0},
            "radius": 5.0,
            "start_angle_deg": 90.0,
            "end_angle_deg": 180.0,
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
        {
            "entity_id": "P1",
            "type": "POINT",
            "point": {"x": 10.0, "y": 5.0},
            "provenance": "GEOMETRY_DERIVED",
            "confidence": 1.0,
        },
    ],
    "constraints": [],
    "dimensions": [],
    "unresolved": [],
    "source_view_ids": ["VIEW-TANGENT-001"],
}


class SolidWorksTangentConstraintMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SolidWorksAgentConfig(
            executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
            output_directory=Path("C:/mrea/output"),
        )

    def request_for(self, entity_ids, *, status="VERIFIED"):
        package = dict(BASE_PACKAGE)
        package["entities"] = [dict(item) for item in BASE_PACKAGE["entities"]]
        package["constraints"] = [
            {
                "constraint_id": "K-TANGENT",
                "type": "TANGENT",
                "entity_ids": list(entity_ids),
                "status": status,
            }
        ]
        mapped = map_sketch_package_v1(package)
        return build_solidworks_agent_request(mapped, self.config)

    def assert_pair_supported(self, first, second):
        request = self.request_for((first, second))
        self.assertEqual(
            request["constraints"],
            [
                {
                    "constraint_id": "K-TANGENT",
                    "type": "TANGENT",
                    "entity_ids": [first, second],
                    "status": "VERIFIED",
                }
            ],
        )

    def test_all_declared_safe_tangent_entity_pairs_are_accepted(self):
        supported_pairs = (
            ("L1", "C1"),
            ("C1", "L1"),
            ("L1", "A1"),
            ("A1", "L1"),
            ("C1", "C2"),
            ("C1", "A1"),
            ("A1", "C1"),
            ("A1", "A2"),
        )
        for pair in supported_pairs:
            with self.subTest(pair=pair):
                self.assert_pair_supported(*pair)

    def test_line_line_is_rejected(self):
        with self.assertRaises(CadAdapterError):
            self.request_for(("L1", "L2"))

    def test_point_participation_is_rejected(self):
        for pair in (("P1", "C1"), ("A1", "P1")):
            with self.subTest(pair=pair):
                with self.assertRaises(CadAdapterError):
                    self.request_for(pair)

    def test_wrong_arity_is_rejected(self):
        for ids in (("C1",), ("L1", "C1", "A1")):
            with self.subTest(entity_ids=ids):
                with self.assertRaises(CadAdapterError):
                    self.request_for(ids)

    def test_duplicate_entity_ids_are_rejected(self):
        with self.assertRaises(CadAdapterError):
            self.request_for(("C1", "C1"))

    def test_unknown_entity_id_is_rejected(self):
        with self.assertRaises(CadAdapterError):
            self.request_for(("L1", "C-UNKNOWN"))

    def test_non_verified_tangent_is_rejected(self):
        with self.assertRaises(CadAdapterError):
            self.request_for(("L1", "C1"), status="DETECTED")


if __name__ == "__main__":
    unittest.main()
