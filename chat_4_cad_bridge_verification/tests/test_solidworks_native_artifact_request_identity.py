from __future__ import annotations

import json
from pathlib import Path
import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentAdapter,
    SolidWorksAgentConfig,
    map_sketch_package_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


def _load_sketch_package() -> dict:
    return json.loads((FIXTURE_ROOT / "sketch_package_v1.json").read_text(encoding="utf-8"))


def _ok_response(sketch_package: dict, *, artifact_sketch_package_id: str | None = None) -> dict:
    dimensions = [item for item in sketch_package["dimensions"] if item["verified"]]
    artifact_owner = artifact_sketch_package_id or sketch_package["sketch_package_id"]
    return {
        "protocol_version": "mrea.solidworks-agent.v1",
        "status": "OK",
        "adapter_name": "SOLIDWORKS_2026",
        "bindings": [
            {
                "dimension_id": item["dimension_id"],
                "measurement_id": item.get("measurement_id"),
                "vendor_dimension_ref": f"MREA_{item['dimension_id']}@Sketch1@Part1.SLDPRT",
            }
            for item in dimensions
        ],
        "read_back": {
            "dimensions": [
                {
                    "dimension_id": item["dimension_id"],
                    "actual_value": item["value"],
                    "unit": item["unit"],
                }
                for item in dimensions
            ],
            "constraint_conflicts": [],
        },
        "artifacts": [
            {
                "artifact_id": f"SWPART-{artifact_owner}",
                "kind": "SOLIDWORKS_PART",
                "uri": f"file:///C:/mrea/{artifact_owner}.SLDPRT",
                "media_type": "application/octet-stream",
                "sha256": "pass18-request-identity-sha256",
                "metadata": {"adapter": "SOLIDWORKS_2026"},
            }
        ],
    }


class FakeRunner:
    def __init__(self, response: dict) -> None:
        self._response = response

    def run(self, request):
        return self._response


class SolidWorksNativeArtifactRequestIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sketch_package = _load_sketch_package()
        cls.mapped = map_sketch_package_v1(cls.sketch_package)

    def transfer(self, response: dict):
        return SolidWorksAgentAdapter(
            SolidWorksAgentConfig(
                executable_path=Path("C:/mrea/Mrea.SolidWorksCadAgent.exe"),
                output_directory=Path("C:/mrea/output"),
            ),
            runner=FakeRunner(response),
        ).transfer(self.mapped)

    def test_native_artifact_identity_matching_request_is_accepted(self) -> None:
        result = self.transfer(_ok_response(self.sketch_package))
        self.assertEqual(
            result.artifacts[0]["artifact_id"],
            f"SWPART-{self.sketch_package['sketch_package_id']}",
        )

    def test_stale_cross_request_native_artifact_identity_fails_closed(self) -> None:
        response = _ok_response(
            self.sketch_package,
            artifact_sketch_package_id="SP-STALE-OTHER-REQUEST",
        )

        with self.assertRaises(CadAdapterError) as captured:
            self.transfer(response)

        self.assertIn("native artifact identity does not match request", str(captured.exception))
        self.assertIn(self.sketch_package["sketch_package_id"], str(captured.exception))
        self.assertIn("SP-STALE-OTHER-REQUEST", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
