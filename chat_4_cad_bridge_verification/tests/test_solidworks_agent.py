from __future__ import annotations

import copy
from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentAdapter,
    SolidWorksAgentConfig,
    build_solidworks_agent_request,
    map_sketch_package_v1,
)


GOLDEN = {
    "schema_version": "mrea.sketch-package.v1",
    "sketch_package_id": "SP-GOLDEN-001",
    "project_id": "P-GOLDEN-001",
    "part_id": "PART-GOLDEN-001",
    "view_id": "VIEW-FRONT-001",
    "coordinate_system": "MAT_XY_MM",
    "entities": [
        {"entity_id": "L-BOTTOM", "type": "LINE", "start": {"x": 0, "y": 0}, "end": {"x": 80.2, "y": 0}, "provenance": "GEOMETRY_DERIVED", "confidence": 1.0},
        {"entity_id": "L-RIGHT", "type": "LINE", "start": {"x": 80.2, "y": 0}, "end": {"x": 80.2, "y": 42.1}, "provenance": "GEOMETRY_DERIVED", "confidence": 1.0},
        {"entity_id": "L-TOP", "type": "LINE", "start": {"x": 80.2, "y": 42.1}, "end": {"x": 0, "y": 42.1}, "provenance": "GEOMETRY_DERIVED", "confidence": 1.0},
        {"entity_id": "L-LEFT", "type": "LINE", "start": {"x": 0, "y": 42.1}, "end": {"x": 0, "y": 0}, "provenance": "GEOMETRY_DERIVED", "confidence": 1.0},
        {"entity_id": "C-HOLE-1", "type": "CIRCLE", "center": {"x": 10.1, "y": 21.05}, "radius": 2.55, "provenance": "GEOMETRY_DERIVED", "confidence": 1.0},
        {"entity_id": "C-HOLE-2", "type": "CIRCLE", "center": {"x": 70.1, "y": 21.05}, "radius": 2.55, "provenance": "GEOMETRY_DERIVED", "confidence": 1.0},
    ],
    "constraints": [],
    "dimensions": [
        {"dimension_id": "D-WIDTH", "measurement_id": "M-WIDTH", "type": "DISTANCE", "value": 80.2, "unit": "mm", "entity_ids": ["L-BOTTOM"], "verified": True, "provenance": "MANUAL_MEASURED"},
        {"dimension_id": "D-HEIGHT", "measurement_id": "M-HEIGHT", "type": "DISTANCE", "value": 42.1, "unit": "mm", "entity_ids": ["L-LEFT"], "verified": True, "provenance": "MANUAL_MEASURED"},
        {"dimension_id": "D-HOLE", "measurement_id": "M-HOLE", "type": "DIAMETER", "value": 5.1, "unit": "mm", "entity_ids": ["C-HOLE-1"], "verified": True, "provenance": "MANUAL_MEASURED"},
        {"dimension_id": "D-CENTER", "measurement_id": "M-CENTER", "type": "DISTANCE", "value": 60.0, "unit": "mm", "entity_ids": ["C-HOLE-1", "C-HOLE-2"], "verified": True, "provenance": "MANUAL_MEASURED"},
    ],
    "unresolved": [],
    "source_view_ids": ["VIEW-FRONT-001"],
}


class FakeRunner:
    def __init__(self, response):
        self.response = response
        self.request = None

    def run(self, request):
        self.request = request
        return self.response


def ok_response():
    values = {
        "D-WIDTH": 80.2,
        "D-HEIGHT": 42.1,
        "D-HOLE": 5.1,
        "D-CENTER": 60.0,
    }
    mids = {
        "D-WIDTH": "M-WIDTH",
        "D-HEIGHT": "M-HEIGHT",
        "D-HOLE": "M-HOLE",
        "D-CENTER": "M-CENTER",
    }
    return {
        "protocol_version": "mrea.solidworks-agent.v1",
        "status": "OK",
        "adapter_name": "SOLIDWORKS_2026",
        "bindings": [
            {
                "dimension_id": did,
                "measurement_id": mids[did],
                "vendor_dimension_ref": f"MREA_{did}@Sketch1@Part1.SLDPRT",
            }
            for did in values
        ],
        "read_back": {
            "dimensions": [
                {"dimension_id": did, "actual_value": value, "unit": "mm"}
                for did, value in values.items()
            ],
            "constraint_conflicts": [],
        },
        "artifacts": [
            {
                "artifact_id": "SWPART-SP-GOLDEN-001",
                "kind": "SOLIDWORKS_PART",
                "uri": "file:///C:/mrea/SP-GOLDEN-001.SLDPRT",
                "media_type": "application/octet-stream",
                "sha256": "abc",
                "metadata": {"adapter": "SOLIDWORKS_2026"},
            }
        ],
    }


class SolidWorksAgentBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.config = SolidWorksAgentConfig(
            executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
            output_directory=Path("C:/mrea/output"),
            part_template_path=Path("C:/templates/Part.prtdot"),
        )

    def mapped(self, package=None):
        return map_sketch_package_v1(package or GOLDEN)

    def test_request_preserves_canonical_mm_values_and_traceability(self):
        request = build_solidworks_agent_request(self.mapped(), self.config)
        self.assertEqual(request["protocol_version"], "mrea.solidworks-agent.v1")
        self.assertEqual(request["adapter_name"], "SOLIDWORKS_2026")
        self.assertEqual(request["dimensions"][0]["dimension_id"], "D-WIDTH")
        self.assertEqual(request["dimensions"][0]["measurement_id"], "M-WIDTH")
        self.assertEqual(request["dimensions"][0]["value"], 80.2)
        self.assertEqual(request["dimensions"][0]["unit"], "mm")

    def test_adapter_maps_agent_response_to_vendor_neutral_result(self):
        runner = FakeRunner(ok_response())
        result = SolidWorksAgentAdapter(self.config, runner=runner).transfer(self.mapped())
        self.assertEqual(result.adapter_name, "SOLIDWORKS_2026")
        self.assertEqual(len(result.bindings), 4)
        self.assertEqual(result.bindings[2].measurement_id, "M-HOLE")
        self.assertEqual(result.read_back.actual_values()["D-CENTER"], 60.0)
        self.assertEqual(result.artifacts[0]["kind"], "SOLIDWORKS_PART")
        self.assertIsNotNone(runner.request)

    def test_relevant_unresolved_measurement_blocks_vendor_transfer(self):
        package = copy.deepcopy(GOLDEN)
        package["unresolved"] = [
            {
                "unresolved_id": "U1",
                "code": "AMBIGUOUS",
                "message": "cannot bind verified measurement",
                "measurement_ids": ["M-HOLE"],
            }
        ]
        with self.assertRaises(CadAdapterError):
            build_solidworks_agent_request(self.mapped(package), self.config)

    def test_relevant_unresolved_entity_blocks_vendor_transfer(self):
        package = copy.deepcopy(GOLDEN)
        package["unresolved"] = [
            {
                "unresolved_id": "U2",
                "code": "AMBIGUOUS",
                "message": "circle unresolved",
                "entity_ids": ["C-HOLE-1"],
            }
        ]
        with self.assertRaises(CadAdapterError):
            build_solidworks_agent_request(self.mapped(package), self.config)

    def test_nonempty_constraints_fail_explicitly_in_pass2_slice(self):
        package = copy.deepcopy(GOLDEN)
        package["constraints"] = [
            {
                "constraint_id": "K1",
                "type": "HORIZONTAL",
                "entity_ids": ["L-BOTTOM"],
                "status": "VERIFIED",
            }
        ]
        with self.assertRaises(CadAdapterError):
            build_solidworks_agent_request(self.mapped(package), self.config)

    def test_unsupported_geometry_is_not_silently_dropped(self):
        package = copy.deepcopy(GOLDEN)
        package["entities"].append(
            {
                "entity_id": "P1",
                "type": "POINT",
                "point": {"x": 1.0, "y": 1.0},
                "provenance": "GEOMETRY_DERIVED",
            }
        )
        with self.assertRaises(CadAdapterError):
            build_solidworks_agent_request(self.mapped(package), self.config)

    def test_non_mm_verified_dimension_is_rejected_before_agent_run(self):
        package = copy.deepcopy(GOLDEN)
        package["dimensions"][0]["unit"] = "deg"
        with self.assertRaises(CadAdapterError):
            build_solidworks_agent_request(self.mapped(package), self.config)

    def test_protocol_mismatch_is_rejected(self):
        response = ok_response()
        response["protocol_version"] = "wrong"
        runner = FakeRunner(response)
        with self.assertRaises(CadAdapterError):
            SolidWorksAgentAdapter(self.config, runner=runner).transfer(self.mapped())

    def test_agent_error_response_is_not_verification_success(self):
        runner = FakeRunner(
            {
                "protocol_version": "mrea.solidworks-agent.v1",
                "status": "ERROR",
                "adapter_name": "SOLIDWORKS_2026",
                "error": {"message": "SOLIDWORKS unavailable"},
            }
        )
        with self.assertRaises(CadAdapterError):
            SolidWorksAgentAdapter(self.config, runner=runner).transfer(self.mapped())


if __name__ == "__main__":
    unittest.main()
