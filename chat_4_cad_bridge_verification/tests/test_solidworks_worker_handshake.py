from __future__ import annotations

from pathlib import Path
import re
from types import SimpleNamespace
import unittest

import mrea_cad_bridge.solidworks_agent as solidworks_agent_module
from mrea_cad_bridge.solidworks_agent import (
    SolidWorksAgentConfig,
    build_solidworks_agent_request,
)
from mrea_cad_bridge.solidworks_constraint_handshake import (
    SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256,
)
from mrea_cad_bridge.solidworks_worker_handshake import (
    SOLIDWORKS_WORKER_CAPABILITIES_SHA256,
    build_solidworks_worker_capability_projection_v1,
    solidworks_worker_capabilities_sha256_v1,
)


EXPECTED_WORKER_SHA256 = "756c37d781e051f0f5b0285a451dc53d2d9d90e98ad3e7b4bfa94924d88dd974"


class SolidWorksWorkerCapabilityHandshakeTests(unittest.TestCase):
    def test_worker_fingerprint_is_deterministic_and_expected(self):
        self.assertEqual(solidworks_worker_capabilities_sha256_v1(), EXPECTED_WORKER_SHA256)
        self.assertEqual(SOLIDWORKS_WORKER_CAPABILITIES_SHA256, EXPECTED_WORKER_SHA256)

    def test_projection_covers_only_worker_compatibility_surface(self):
        projection = build_solidworks_worker_capability_projection_v1()
        self.assertEqual(
            set(projection),
            {
                "schema_version",
                "adapter_name",
                "geometry_entities",
                "verified_dimensions",
                "verified_dimension_rules",
                "constraints",
                "protocols",
            },
        )
        self.assertEqual(projection["protocols"], {"agent": "mrea.solidworks-agent.v1"})
        self.assertEqual(
            projection["geometry_entities"]["supported"],
            ["POINT", "LINE", "CIRCLE", "ARC"],
        )
        self.assertEqual(
            projection["verified_dimensions"]["supported"],
            ["DISTANCE", "DIAMETER", "RADIUS", "ANGLE"],
        )
        self.assertEqual(
            projection["verified_dimension_rules"]["schema_version"],
            "mrea.solidworks-dimension-rules.v1",
        )
        self.assertEqual(
            projection["verified_dimension_rules"]["types"]["DIAMETER"]["entity_type_patterns"],
            [["CIRCLE"]],
        )
        self.assertNotIn("runtime", projection)
        self.assertNotIn("host_readiness", projection["protocols"])

    def test_projection_is_caller_safe(self):
        projection = build_solidworks_worker_capability_projection_v1()
        projection["geometry_entities"]["supported"].append("MUTATED")
        projection["constraints"]["supported"].clear()
        projection["verified_dimension_rules"]["types"]["RADIUS"]["entity_type_patterns"].clear()

        fresh = build_solidworks_worker_capability_projection_v1()
        self.assertNotIn("MUTATED", fresh["geometry_entities"]["supported"])
        self.assertIn("TANGENT", fresh["constraints"]["supported"])
        self.assertEqual(
            fresh["verified_dimension_rules"]["types"]["RADIUS"]["entity_type_patterns"],
            [["CIRCLE"], ["ARC"]],
        )
        self.assertEqual(solidworks_worker_capabilities_sha256_v1(), EXPECTED_WORKER_SHA256)

    def test_python_preflight_support_sets_are_derived_from_projection(self):
        projection = build_solidworks_worker_capability_projection_v1()
        self.assertEqual(
            solidworks_agent_module._SUPPORTED_ENTITY_TYPES,
            frozenset(projection["geometry_entities"]["supported"]),
        )
        self.assertEqual(
            solidworks_agent_module._SUPPORTED_DIMENSION_TYPES,
            frozenset(projection["verified_dimensions"]["supported"]),
        )

    def test_agent_request_carries_full_and_constraint_fingerprints(self):
        package = SimpleNamespace(
            sketch_package_id="SP-WORKER-HANDSHAKE-001",
            expected_dimensions=(),
            dimensions=(),
            unresolved=(),
            entity_contracts=(),
            constraints=(),
        )
        config = SolidWorksAgentConfig(
            executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
            output_directory=Path("C:/mrea/output"),
        )

        request = build_solidworks_agent_request(package, config)

        self.assertEqual(request["worker_capabilities_sha256"], EXPECTED_WORKER_SHA256)
        self.assertEqual(
            request["constraint_capabilities_sha256"],
            SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256,
        )

    def test_csharp_worker_embeds_same_hash_and_checks_before_com(self):
        root = Path(__file__).resolve().parents[1]
        program = (root / "solidworks_agent" / "Program.cs").read_text(encoding="utf-8")
        match = re.search(
            r'WorkerCapabilitiesSha256\s*=\s*"([0-9a-f]{64})"',
            program,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), EXPECTED_WORKER_SHA256)

        validate_start = program.index("private static void ValidateRequestEnvelope")
        validate_end = program.index("private static void ValidateDimensionEnvelope")
        validate_body = program[validate_start:validate_end]
        self.assertIn("request.worker_capabilities_sha256", validate_body)
        self.assertIn("Worker capability fingerprint mismatch", validate_body)
        self.assertIn("ValidateDimensionEnvelope(request);", validate_body)
        self.assertLess(
            validate_body.index("request.worker_capabilities_sha256"),
            validate_body.index("request.constraint_capabilities_sha256"),
        )
        self.assertLess(
            program.index("ValidateRequestEnvelope(request);"),
            program.index("SolidWorksSession.Open(request)"),
        )
        self.assertLess(
            program.index("ValidateDimensionEnvelope(request);"),
            program.index("SolidWorksSession.Open(request)"),
        )

    def test_csharp_dimension_envelope_matches_declared_rules(self):
        root = Path(__file__).resolve().parents[1]
        program = (root / "solidworks_agent" / "Program.cs").read_text(encoding="utf-8")
        projection = build_solidworks_worker_capability_projection_v1()
        rules = projection["verified_dimension_rules"]

        envelope_start = program.index("private static void ValidateDimensionEnvelope")
        envelope_end = program.index("private static void RequireDimensionUnit")
        envelope = program[envelope_start:envelope_end]

        for dimension_type in rules["types"]:
            self.assertIn(f'dimension.type == "{dimension_type}"', envelope)
        self.assertIn("Dimension contains duplicate entity_ids", envelope)
        self.assertIn("DISTANCE supports one LINE or two CIRCLE/ARC entities", envelope)
        self.assertIn("DIAMETER requires exactly one CIRCLE", envelope)
        self.assertIn("RADIUS requires exactly one CIRCLE/ARC", envelope)
        self.assertIn("ANGLE dimension requires exactly two LINE entities", envelope)
        self.assertIn("ANGLE dimension requires 0 < value < 180 deg", envelope)
        self.assertGreaterEqual(envelope.count('RequireDimensionUnit(dimension, "mm")'), 3)
        self.assertEqual(envelope.count('RequireDimensionUnit(dimension, "deg")'), 1)

        angle_geometry = rules["types"]["ANGLE"]["geometry"]
        self.assertEqual(angle_geometry["normalized_cross_min"], 1e-10)
        self.assertIn("Math.Abs(cross) / scale < 1e-10", program)

    def test_csharp_entity_and_dimension_type_guards_match_projection(self):
        root = Path(__file__).resolve().parents[1]
        transfer = (root / "solidworks_agent" / "SolidWorksTransfer.cs").read_text(
            encoding="utf-8"
        )
        projection = build_solidworks_worker_capability_projection_v1()

        entity_match = re.search(
            r'if \((?P<condition>entity\.type != .*?)\)\s*'
            r'throw new NotSupportedException\("Vendor agent supports POINT/LINE/CIRCLE/ARC only:',
            transfer,
            flags=re.S,
        )
        self.assertIsNotNone(entity_match)
        csharp_entities = set(
            re.findall(r'entity\.type != "([A-Z]+)"', entity_match.group("condition"))
        )
        self.assertEqual(
            csharp_entities,
            set(projection["geometry_entities"]["supported"]),
        )

        dimension_match = re.search(
            r'if \((?P<condition>dimension\.type != .*?)\)\s*'
            r'throw new NotSupportedException\("Unsupported dimension type:',
            transfer,
            flags=re.S,
        )
        self.assertIsNotNone(dimension_match)
        csharp_dimensions = set(
            re.findall(
                r'dimension\.type != "([A-Z]+)"',
                dimension_match.group("condition"),
            )
        )
        self.assertEqual(
            csharp_dimensions,
            set(projection["verified_dimensions"]["supported"]),
        )
        self.assertIn('if (dimension.unit != "deg")', transfer)
        self.assertIn('else if (dimension.unit != "mm")', transfer)
        self.assertEqual(
            set(projection["verified_dimensions"]["units"].values()),
            {"mm", "deg"},
        )

    def test_csharp_relation_mapping_matches_declared_supported_constraints(self):
        root = Path(__file__).resolve().parents[1]
        transfer = (root / "solidworks_agent" / "SolidWorksTransfer.cs").read_text(
            encoding="utf-8"
        )
        projection = build_solidworks_worker_capability_projection_v1()

        relation_start = transfer.index("private static string RelationId")
        relation_end = transfer.index("private static dynamic CreateEntity")
        relation_body = transfer[relation_start:relation_end]
        relation_types = set(re.findall(r'case "([A-Z]+)"', relation_body))
        self.assertEqual(
            relation_types,
            set(projection["constraints"]["supported"]),
        )

    def test_protocol_model_carries_worker_fingerprint_field(self):
        root = Path(__file__).resolve().parents[1]
        protocol = (root / "solidworks_agent" / "ProtocolModels.cs").read_text(encoding="utf-8")
        self.assertIn(
            "public string worker_capabilities_sha256 { get; set; }",
            protocol,
        )


if __name__ == "__main__":
    unittest.main()
