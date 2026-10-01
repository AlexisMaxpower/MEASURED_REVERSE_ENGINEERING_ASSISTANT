from __future__ import annotations

from pathlib import Path
import re
from types import SimpleNamespace
import unittest

from mrea_cad_bridge.solidworks_agent import (
    SolidWorksAgentConfig,
    build_solidworks_agent_request,
)
from mrea_cad_bridge.solidworks_constraint_handshake import (
    SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256,
    solidworks_constraint_capabilities_sha256_v1,
)


EXPECTED_SHA256 = "5eac12828b4255e05b17732093bf881e24a64c016abe5828573e4235be665ae4"


class SolidWorksConstraintCapabilityHandshakeTests(unittest.TestCase):
    def test_python_fingerprint_is_deterministic_and_expected(self):
        self.assertEqual(solidworks_constraint_capabilities_sha256_v1(), EXPECTED_SHA256)
        self.assertEqual(SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256, EXPECTED_SHA256)

    def test_agent_request_carries_constraint_capability_fingerprint(self):
        package = SimpleNamespace(
            sketch_package_id="SP-HANDSHAKE-001",
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
        self.assertEqual(request["constraint_capabilities_sha256"], EXPECTED_SHA256)

    def test_csharp_worker_embeds_same_fingerprint_and_rejects_mismatch(self):
        root = Path(__file__).resolve().parents[1]
        program = (root / "solidworks_agent" / "Program.cs").read_text(encoding="utf-8")
        match = re.search(
            r'ConstraintCapabilitiesSha256\s*=\s*"([0-9a-f]{64})"',
            program,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), EXPECTED_SHA256)

        validate_start = program.index("private static void ValidateRequestEnvelope")
        validate_end = program.index("private static void ValidateEntityEnvelope")
        validate_body = program[validate_start:validate_end]
        self.assertIn("request.constraint_capabilities_sha256", validate_body)
        self.assertIn("Constraint capability fingerprint mismatch", validate_body)
        self.assertIn("ValidateConstraintEnvelope(request);", validate_body)
        self.assertLess(
            validate_body.index("request.constraint_capabilities_sha256"),
            validate_body.index("ValidateConstraintEnvelope(request);"),
        )

        main_start = program.index("private static int Main")
        main_end = program.index("private static JavaScriptSerializer NewSerializer")
        main_body = program[main_start:main_end]
        self.assertLess(
            main_body.index("ValidateRequestEnvelope(request);"),
            main_body.index("SolidWorksSession.Open(request)"),
        )

    def test_csharp_constraint_envelope_contains_declared_fail_closed_subset(self):
        root = Path(__file__).resolve().parents[1]
        program = (root / "solidworks_agent" / "Program.cs").read_text(encoding="utf-8")
        start = program.index("private static void ValidateConstraintEnvelope")
        end = program.index("private static void ValidateDimensionEnvelope")
        envelope = program[start:end]

        for constraint_type in (
            "HORIZONTAL",
            "VERTICAL",
            "PARALLEL",
            "PERPENDICULAR",
            "CONCENTRIC",
            "EQUAL",
        ):
            self.assertIn(f'constraint.type == "{constraint_type}"', envelope)
        self.assertIn('constraint.type != "TANGENT"', envelope)
        self.assertIn("Duplicate constraint_id", envelope)
        self.assertIn("Constraint contains duplicate entity_ids", envelope)
        self.assertIn("Constraint references unknown entity", envelope)
        self.assertIn("Real-host constraint must be VERIFIED", envelope)
        self.assertIn("requires exactly one LINE", envelope)
        self.assertIn("requires exactly two LINE entities", envelope)
        self.assertIn("CONCENTRIC requires exactly two CIRCLE/ARC entities", envelope)
        self.assertIn("TANGENT supports LINE/CIRCLE/ARC pairs with at least one CIRCLE/ARC", envelope)

    def test_protocol_model_carries_fingerprint_field(self):
        root = Path(__file__).resolve().parents[1]
        protocol = (root / "solidworks_agent" / "ProtocolModels.cs").read_text(encoding="utf-8")
        self.assertIn(
            "public string constraint_capabilities_sha256 { get; set; }",
            protocol,
        )


if __name__ == "__main__":
    unittest.main()
