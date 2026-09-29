from __future__ import annotations

from ..adapter import CadArtifact
from ..model import ArcEntity, CadEntity, CadSketch, CircleEntity, LineEntity, PointEntity, PolylineEntity


def _fmt(value: float) -> str:
    if abs(value) < 5e-13:
        value = 0.0
    text = f"{value:.9f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def _pair(code: int, value: str | float | int) -> list[str]:
    return [str(code), _fmt(value) if isinstance(value, float) else str(value)]


class DxfExporter:
    """Dependency-free ASCII DXF R12 exporter for the Chat 4 internal CAD model."""

    format_name = "DXF"
    file_extension = ".dxf"
    media_type = "application/dxf"

    def export(self, sketch: CadSketch) -> CadArtifact:
        lines: list[str] = []
        lines += _pair(0, "SECTION") + _pair(2, "HEADER")
        lines += _pair(999, "MREA internal CAD bridge; units=mm")
        lines += _pair(0, "ENDSEC")
        lines += _pair(0, "SECTION") + _pair(2, "ENTITIES")

        for entity in sketch.deterministic_entities():
            lines += self._render_entity(entity)

        lines += _pair(0, "ENDSEC") + _pair(0, "EOF")
        return CadArtifact(
            format_name=self.format_name,
            file_extension=self.file_extension,
            media_type=self.media_type,
            content="\n".join(lines) + "\n",
        )

    def _common(self, entity: CadEntity) -> list[str]:
        layer = "CONSTRUCTION" if entity.construction else "0"
        return _pair(8, layer) + _pair(5, entity.entity_id)

    def _render_entity(self, entity: CadEntity) -> list[str]:
        if isinstance(entity, PointEntity):
            return (
                _pair(0, "POINT")
                + self._common(entity)
                + _pair(10, entity.point.x)
                + _pair(20, entity.point.y)
                + _pair(30, 0.0)
            )
        if isinstance(entity, LineEntity):
            return (
                _pair(0, "LINE")
                + self._common(entity)
                + _pair(10, entity.start.x)
                + _pair(20, entity.start.y)
                + _pair(30, 0.0)
                + _pair(11, entity.end.x)
                + _pair(21, entity.end.y)
                + _pair(31, 0.0)
            )
        if isinstance(entity, CircleEntity):
            return (
                _pair(0, "CIRCLE")
                + self._common(entity)
                + _pair(10, entity.center.x)
                + _pair(20, entity.center.y)
                + _pair(30, 0.0)
                + _pair(40, entity.radius)
            )
        if isinstance(entity, ArcEntity):
            return (
                _pair(0, "ARC")
                + self._common(entity)
                + _pair(10, entity.center.x)
                + _pair(20, entity.center.y)
                + _pair(30, 0.0)
                + _pair(40, entity.radius)
                + _pair(50, entity.start_angle_deg % 360.0)
                + _pair(51, entity.end_angle_deg % 360.0)
            )
        if isinstance(entity, PolylineEntity):
            output = _pair(0, "POLYLINE") + self._common(entity) + _pair(66, 1) + _pair(70, 1 if entity.closed else 0)
            for point in entity.points:
                output += (
                    _pair(0, "VERTEX")
                    + _pair(8, "CONSTRUCTION" if entity.construction else "0")
                    + _pair(10, point.x)
                    + _pair(20, point.y)
                    + _pair(30, 0.0)
                )
            output += _pair(0, "SEQEND") + _pair(8, "CONSTRUCTION" if entity.construction else "0")
            return output
        raise TypeError(f"unsupported CAD entity: {type(entity).__name__}")
