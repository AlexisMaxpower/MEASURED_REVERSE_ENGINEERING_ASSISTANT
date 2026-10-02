from __future__ import annotations

from pathlib import Path
import unittest


class SolidWorksReadBackValueGateTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.transfer = (root / "solidworks_agent" / "SolidWorksTransfer.cs").read_text(
            encoding="utf-8"
        )
        self.program = (root / "solidworks_agent" / "Program.cs").read_text(
            encoding="utf-8"
        )

    def test_system_value_readback_is_guarded_before_normalization(self) -> None:
        self.assertIn(
            "var systemValue = RequireFiniteSystemValue(raw, spec.dimension_id);",
            self.transfer,
        )
        self.assertNotIn("var systemValue = FirstDouble(raw);", self.transfer)
        self.assertNotIn("private static double FirstDouble", self.transfer)

    def test_guard_rejects_missing_ambiguous_non_numeric_and_non_finite_payloads(self) -> None:
        start = self.transfer.index("private static double RequireFiniteSystemValue")
        end = self.transfer.index("private static string Sha256", start)
        helper = self.transfer[start:end]

        self.assertIn("if (raw == null)", helper)
        self.assertIn("array == null || array.Length != 1", helper)
        self.assertIn("if (!(first is double))", helper)
        self.assertIn("double.IsNaN(value) || double.IsInfinity(value)", helper)
        self.assertIn("SOLIDWORKS returned no system value for dimension", helper)
        self.assertIn("SOLIDWORKS returned an unexpected system-value payload", helper)
        self.assertIn("SOLIDWORKS returned a non-numeric system value", helper)
        self.assertIn("SOLIDWORKS returned a non-finite system value", helper)

    def test_guard_failure_remains_in_cad_transfer_error_class(self) -> None:
        execute_start = self.program.index("response = SolidWorksTransfer.Execute(session, request);")
        execute_end = self.program.index("response.real_host_executed = true;", execute_start)
        transfer_error_path = self.program[execute_start:execute_end]

        self.assertIn("ExitCadTransfer", transfer_error_path)
        self.assertIn('"CAD_TRANSFER_FAILED"', transfer_error_path)


if __name__ == "__main__":
    unittest.main()
