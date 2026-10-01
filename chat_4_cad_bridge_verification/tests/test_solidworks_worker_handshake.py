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
)
from mrea_cad_bridge.solidworks_worker_handshake import (
    SOLIDWORKS_WORKER_CAPABILITIES_SHA256,
    build_solidworks_worker_capability_projection_v1,
    solidworks_worker_capabilities_sha256_v1,
)


EXPECTED_WORKER_SHA256 = "1713a8671cc358c54af5664fb1144789ba85b50291d2b02e479aa568a14ae4bd"


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
        self.assertNotIn("runtime", projection)
        self.assertNotIn("host_readiness", projection["protocols"])

    def test_projection_is_caller_safe(self):
        projection = build_solidworks_worker_capability_projection_v1()
        projection["geometry_entities"]["supported"].append("MUTATED")
        projection["constraints"]["supported"].clear()

        fresh = build_solidworks_worker_capability_projection_v1()
        self.assertNotIn("MUTATED", fresh["geometry_entities"]["supported"])
        self.assertIn("TANGENT", fresh["constraints"]["supported"])
        self.assertEqual(solidworks_worker_capabilities_sha256_v1(), EXPECTED_WORKER_SHA256)

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
        validate_end = program.index("private static string StartupFailureCode")
        validate_body = program[validate_start:validate_end]
        self.assertIn("request.worker_capabilities_sha256", validate_body)
        self.assertIn("Worker capability fingerprint mismatch", validate_body)
        self.assertLess(
            validate_body.index("request.worker_capabilities_sha256"),
            validate_body.index("request.constraint_capabilities_sha256"),
        )
        self.assertLess(
            program.index("ValidateRequestEnvelope(request);"),
            program.index("SolidWorksSession.Open(request)"),
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
