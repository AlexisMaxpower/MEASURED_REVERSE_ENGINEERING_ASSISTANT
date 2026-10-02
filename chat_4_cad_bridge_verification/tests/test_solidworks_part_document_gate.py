from __future__ import annotations

from pathlib import Path
import unittest


class SolidWorksPartDocumentGateTests(unittest.TestCase):
    def test_new_document_must_be_a_part_before_front_plane_or_sketch_work(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "solidworks_agent" / "SolidWorksSession.cs").read_text(
            encoding="utf-8"
        )

        self.assertIn("using SolidWorks.Interop.sldworks;", source)
        create_index = source.index("model = app.NewDocument(")
        null_guard_index = source.index("if (model == null)", create_index)
        type_read_index = source.index(
            "var documentType = ((IModelDoc2)model).GetType();", null_guard_index
        )
        type_guard_index = source.index(
            "if (documentType != (int)swDocumentTypes_e.swDocPART)", type_read_index
        )
        front_plane_index = source.index(
            "SelectFrontPlaneWithoutLocalizedName(app, model);", type_guard_index
        )

        self.assertLess(create_index, null_guard_index)
        self.assertLess(null_guard_index, type_read_index)
        self.assertLess(type_read_index, type_guard_index)
        self.assertLess(type_guard_index, front_plane_index)

        guard = source[type_guard_index:front_plane_index]
        self.assertIn("SOLIDWORKS part template created a non-part document", guard)
        self.assertIn("actual document type=", guard)
        self.assertIn("template=", guard)

    def test_wrong_document_type_uses_existing_template_startup_failure_class(self):
        root = Path(__file__).resolve().parents[1]
        program = (root / "solidworks_agent" / "Program.cs").read_text(
            encoding="utf-8"
        )
        session = (root / "solidworks_agent" / "SolidWorksSession.cs").read_text(
            encoding="utf-8"
        )

        self.assertIn("part template created a non-part document", session)
        self.assertIn('message.IndexOf("template", StringComparison.OrdinalIgnoreCase)', program)
        self.assertIn('return "PART_TEMPLATE_UNAVAILABLE";', program)

    def test_failed_open_cleanup_still_wraps_document_type_guard(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "solidworks_agent" / "SolidWorksSession.cs").read_text(
            encoding="utf-8"
        )

        guard_index = source.index(
            "if (documentType != (int)swDocumentTypes_e.swDocPART)"
        )
        catch_index = source.index("catch\n            {", guard_index)
        cleanup_index = source.index("CleanupFailedOpen(app, model, launched);", catch_index)
        self.assertLess(guard_index, catch_index)
        self.assertLess(catch_index, cleanup_index)


if __name__ == "__main__":
    unittest.main()
