from __future__ import annotations

from pathlib import Path
import unittest


class SolidWorksRebuildFailureGateTests(unittest.TestCase):
    def test_every_transfer_rebuild_is_checked_and_fails_closed(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "solidworks_agent" / "SolidWorksTransfer.cs").read_text(
            encoding="utf-8"
        )

        self.assertEqual(source.count("EditRebuild3()"), 1)
        self.assertIn(
            'RequireSuccessfulRebuild(model, "final sketch before native save/read-back");',
            source,
        )
        self.assertIn(
            'RequireSuccessfulRebuild(model, "constraint " + constraint.constraint_id);',
            source,
        )

        start = source.index("private static void RequireSuccessfulRebuild")
        end = source.index("private static void SaveNativePart", start)
        helper = source[start:end]
        self.assertIn("var rebuilt = (bool)model.EditRebuild3();", helper)
        self.assertIn("if (!rebuilt)", helper)
        self.assertIn(
            'throw new InvalidOperationException("SOLIDWORKS rebuild failed: " + context);',
            helper,
        )

    def test_rebuild_failure_remains_in_transfer_error_class(self):
        root = Path(__file__).resolve().parents[1]
        program = (root / "solidworks_agent" / "Program.cs").read_text(encoding="utf-8")

        execute_start = program.index("response = SolidWorksTransfer.Execute(session, request);")
        execute_end = program.index("response.real_host_executed = true;", execute_start)
        transfer_error_path = program[execute_start:execute_end]
        self.assertIn("ExitCadTransfer", transfer_error_path)
        self.assertIn('"CAD_TRANSFER_FAILED"', transfer_error_path)


if __name__ == "__main__":
    unittest.main()
