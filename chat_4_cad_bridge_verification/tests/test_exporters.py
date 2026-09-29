from io import StringIO
import unittest

import ezdxf

from mrea_cad_bridge import (
    ArcEntity,
    CadSketch,
    CircleEntity,
    DxfExporter,
    LineEntity,
    Point2D,
    PolylineEntity,
    SvgExporter,
)


class ExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sketch = CadSketch(
            entities=(
                CircleEntity("C2", Point2D(10.0, 10.0), 2.5),
                LineEntity("L1", Point2D(0.0, 0.0), Point2D(20.0, 0.0)),
                ArcEntity("A1", Point2D(5.0, 5.0), 3.0, 0.0, 90.0),
                PolylineEntity(
                    "P1",
                    (Point2D(0.0, 0.0), Point2D(0.0, 5.0), Point2D(5.0, 5.0)),
                    construction=True,
                ),
            )
        )

    def test_svg_is_deterministic_and_contains_supported_entities(self) -> None:
        exporter = SvgExporter(margin_mm=1.0)
        first = exporter.export(self.sketch)
        second = exporter.export(self.sketch)
        self.assertEqual(first.content, second.content)
        self.assertEqual(first.file_extension, ".svg")
        self.assertIn('id="L1"', first.content)
        self.assertIn('id="C2"', first.content)
        self.assertIn('id="A1"', first.content)
        self.assertIn('id="P1"', first.content)
        self.assertIn('stroke-dasharray="1,1"', first.content)

    def test_dxf_is_deterministic_parseable_and_contains_supported_entities(self) -> None:
        exporter = DxfExporter()
        first = exporter.export(self.sketch)
        second = exporter.export(self.sketch)
        self.assertEqual(first.content, second.content)
        self.assertEqual(first.file_extension, ".dxf")

        document = ezdxf.read(StringIO(first.content))
        entities = list(document.modelspace())
        self.assertEqual([entity.dxftype() for entity in entities], ["ARC", "CIRCLE", "LINE", "POLYLINE"])
        self.assertEqual(entities[-1].dxf.linetype, "DASHED")

    def test_sketch_rejects_duplicate_entity_ids(self) -> None:
        with self.assertRaises(ValueError):
            CadSketch(
                entities=(
                    LineEntity("E1", Point2D(0, 0), Point2D(1, 0)),
                    CircleEntity("E1", Point2D(0, 0), 1),
                )
            )


if __name__ == "__main__":
    unittest.main()
