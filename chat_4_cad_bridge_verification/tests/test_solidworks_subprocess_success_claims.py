from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mrea_cad_bridge import (
    CadAdapterError,
    SolidWorksAgentConfig,
    SubprocessSolidWorksAgentRunner,
)


class SolidWorksSubprocessSuccessClaimsTests(unittest.TestCase):
    def _run_response(self, response, *, process_returncode: int = 0):
        with tempfile.TemporaryDirectory(prefix="mrea-pass19-") as temp_dir:
            root = Path(temp_dir)
            executable = root / "Mrea.SolidWorksCadAgent.exe"
            executable.write_bytes(b"test-double")
            output_dir = root / "output"
            runner = SubprocessSolidWorksAgentRunner(
                SolidWorksAgentConfig(
                    executable_path=executable,
                    output_directory=output_dir,
                )
            )

            def fake_subprocess_run(args, **kwargs):
                response_path = Path(args[args.index("--response") + 1])
                response_path.write_text(json.dumps(response), encoding="utf-8")
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=process_returncode,
                    stdout="",
                    stderr="",
                )

            with patch(
                "mrea_cad_bridge.solidworks_agent.subprocess.run",
                side_effect=fake_subprocess_run,
            ):
                return runner.run({"protocol_version": "test-request"})

    @staticmethod
    def _ok_response() -> dict:
        return {
            "status": "OK",
            "real_host_executed": True,
            "solidworks_version": "34.0.1",
            "exit_code": 0,
        }

    def test_complete_subprocess_success_claims_are_accepted(self) -> None:
        response = self._ok_response()
        actual = self._run_response(response)
        self.assertEqual(actual, response)

    def test_success_requires_real_host_executed_true(self) -> None:
        for value in (None, False, 1, "true"):
            with self.subTest(value=value):
                response = self._ok_response()
                if value is None:
                    response.pop("real_host_executed")
                else:
                    response["real_host_executed"] = value

                with self.assertRaises(CadAdapterError) as captured:
                    self._run_response(response)

                self.assertIn("real_host_executed=true", str(captured.exception))

    def test_success_requires_integer_zero_response_exit_code(self) -> None:
        for value in (None, 1, -1, "0", True):
            with self.subTest(value=value):
                response = self._ok_response()
                if value is None:
                    response.pop("exit_code")
                else:
                    response["exit_code"] = value

                with self.assertRaises(CadAdapterError) as captured:
                    self._run_response(response)

                self.assertIn("exit_code=0", str(captured.exception))

    def test_success_requires_solidworks_2026_revision_major(self) -> None:
        for value in (None, "", "not-a-version", "33.5.0", "35.0.0"):
            with self.subTest(value=value):
                response = self._ok_response()
                if value is None:
                    response.pop("solidworks_version")
                else:
                    response["solidworks_version"] = value

                with self.assertRaises(CadAdapterError):
                    self._run_response(response)

    def test_nonzero_process_returncode_cannot_claim_ok(self) -> None:
        with self.assertRaises(CadAdapterError) as captured:
            self._run_response(self._ok_response(), process_returncode=40)

        self.assertIn("exited non-zero while claiming OK", str(captured.exception))

    def test_failure_response_is_not_promoted_by_success_claim_gate(self) -> None:
        response = {
            "status": "ERROR",
            "real_host_executed": False,
            "solidworks_version": None,
            "exit_code": 30,
            "error": {"message": "SOLIDWORKS unavailable"},
        }
        actual = self._run_response(response, process_returncode=30)
        self.assertEqual(actual, response)

    def test_response_json_must_be_object(self) -> None:
        with self.assertRaises(CadAdapterError) as captured:
            self._run_response(["not", "an", "object"])

        self.assertIn("response JSON must be an object", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
