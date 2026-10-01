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


EXPECTED_SHA256 = "02a33af48298669e3563ce467b6cd6d8f2586d073baa3de6baa45749fc92a3d8"


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
        validate_end = program.index("private static string StartupFailureCode")
        validate_body = program[validate_start:validate_end]
        self.assertIn("request.constraint_capabilities_sha256", validate_body)
        self.assertIn("Constraint capability fingerprint mismatch", validate_body)

        self.assertLess(
            program.index("ValidateRequestEnvelope(request);"),
            program.index("SolidWorksSession.Open(request)"),
        )

    def test_protocol_model_carries_fingerprint_field(self):
        root = Path(__file__).resolve().parents[1]
        protocol = (root / "solidworks_agent" / "ProtocolModels.cs").read_text(encoding="utf-8")
        self.assertIn(
            "public string constraint_capabilities_sha256 { get; set; }",
            protocol,
        )


if __name__ == "__main__":
    unittest.main()
