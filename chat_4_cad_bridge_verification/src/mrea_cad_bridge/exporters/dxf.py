from __future__ import annotations

from io import StringIO

from ezdxf.addons.r12writer import r12writer

from ..adapter import CadArtifact
from ..model import ArcEntity, CadEntity, CadSketch, CircleEntity, LineEntity, PointEntity, PolylineEntity


class DxfExporter:
    """ASCII DXF R12 exporter backed by ezdxf's restricted R12 writer."""

    format_name = "DXF"
    file_extension = ".dxf"
    media_type = "application/dxf"

    def export(self, sketch: CadSketch) -> CadArtifact:
        stream = StringIO()
        with r12writer(stream, fixed_tables=True) as writer:
            for entity in sketch.deterministic_entities():
                self._write_entity(writer, entity)

        return CadArtifact(
            format_name=self.format_name,
            file_extension=self.file_extension,
            media_type=self.media_type,
            content=stream.getvalue(),
        )

    def _write_entity(self, writer, entity: CadEntity) -> None:
        linetype = "DASHED" if entity.construction else None

        if isinstance(entity, PointEntity):
            writer.add_point(
                (entity.point.x, entity.point.y),
                layer="0",
                linetype=linetype,
            )
            return
        if isinstance(entity, LineEntity):
            writer.add_line(
                (entity.start.x, entity.start.y),
                (entity.end.x, entity.end.y),
                layer="0",
                linetype=linetype,
            )
            return
        if isinstance(entity, CircleEntity):
            writer.add_circle(
                (entity.center.x, entity.center.y),
                entity.radius,
                layer="0",
                linetype=linetype,
            )
            return
        if isinstance(entity, ArcEntity):
            writer.add_arc(
                (entity.center.x, entity.center.y),
                entity.radius,
                start=entity.start_angle_deg,
                end=entity.end_angle_deg,
                layer="0",
                linetype=linetype,
            )
            return
        if isinstance(entity, PolylineEntity):
            writer.add_polyline_2d(
                [(point.x, point.y) for point in entity.points],
                format="xy",
                closed=entity.closed,
                layer="0",
                linetype=linetype,
            )
            return
        raise TypeError(f"unsupported CAD entity: {type(entity).__name__}")
