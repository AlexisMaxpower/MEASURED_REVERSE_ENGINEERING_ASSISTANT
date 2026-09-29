from __future__ import annotations

from html import escape
from math import cos, radians, sin

from ..adapter import CadArtifact
from ..model import ArcEntity, CadEntity, CadSketch, CircleEntity, LineEntity, PointEntity, PolylineEntity


def _fmt(value: float) -> str:
    if abs(value) < 5e-13:
        value = 0.0
    text = f"{value:.9f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def _entity_bounds(entity: CadEntity) -> tuple[float, float, float, float]:
    if isinstance(entity, PointEntity):
        return entity.point.x, entity.point.y, entity.point.x, entity.point.y
    if isinstance(entity, LineEntity):
        return (
            min(entity.start.x, entity.end.x),
            min(entity.start.y, entity.end.y),
            max(entity.start.x, entity.end.x),
            max(entity.start.y, entity.end.y),
        )
    if isinstance(entity, CircleEntity | ArcEntity):
        return (
            entity.center.x - entity.radius,
            entity.center.y - entity.radius,
            entity.center.x + entity.radius,
            entity.center.y + entity.radius,
        )
    if isinstance(entity, PolylineEntity):
        xs = [point.x for point in entity.points]
        ys = [point.y for point in entity.points]
        return min(xs), min(ys), max(xs), max(ys)
    raise TypeError(f"unsupported CAD entity: {type(entity).__name__}")


def _arc_endpoint(entity: ArcEntity, angle_deg: float) -> tuple[float, float]:
    angle = radians(angle_deg)
    return (
        entity.center.x + entity.radius * cos(angle),
        entity.center.y + entity.radius * sin(angle),
    )


class SvgExporter:
    format_name = "SVG"
    file_extension = ".svg"
    media_type = "image/svg+xml"

    def __init__(self, margin_mm: float = 5.0) -> None:
        if margin_mm < 0:
            raise ValueError("margin_mm must be >= 0")
        self._margin_mm = margin_mm

    def export(self, sketch: CadSketch) -> CadArtifact:
        entities = sketch.deterministic_entities()
        if not entities:
            min_x = min_y = 0.0
            max_x = max_y = 1.0
        else:
            bounds = [_entity_bounds(entity) for entity in entities]
            min_x = min(item[0] for item in bounds)
            min_y = min(item[1] for item in bounds)
            max_x = max(item[2] for item in bounds)
            max_y = max(item[3] for item in bounds)

        min_x -= self._margin_mm
        min_y -= self._margin_mm
        max_x += self._margin_mm
        max_y += self._margin_mm
        width = max(max_x - min_x, 1e-9)
        height = max(max_y - min_y, 1e-9)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="{_fmt(min_x)} {_fmt(-max_y)} {_fmt(width)} {_fmt(height)}" '
                f'width="{_fmt(width)}mm" height="{_fmt(height)}mm">'
            ),
            '  <g fill="none" stroke="black" stroke-width="0.2" transform="scale(1,-1)">',
        ]

        for entity in entities:
            lines.append("    " + self._render_entity(entity))

        lines.extend(["  </g>", "</svg>", ""])
        return CadArtifact(
            format_name=self.format_name,
            file_extension=self.file_extension,
            media_type=self.media_type,
            content="\n".join(lines),
        )

    def _render_entity(self, entity: CadEntity) -> str:
        entity_id = escape(entity.entity_id, quote=True)
        dash = ' stroke-dasharray="1,1"' if entity.construction else ""

        if isinstance(entity, PointEntity):
            return (
                f'<circle id="{entity_id}" cx="{_fmt(entity.point.x)}" cy="{_fmt(entity.point.y)}" '
                f'r="0.25"{dash}/>'
            )
        if isinstance(entity, LineEntity):
            return (
                f'<line id="{entity_id}" x1="{_fmt(entity.start.x)}" y1="{_fmt(entity.start.y)}" '
                f'x2="{_fmt(entity.end.x)}" y2="{_fmt(entity.end.y)}"{dash}/>'
            )
        if isinstance(entity, CircleEntity):
            return (
                f'<circle id="{entity_id}" cx="{_fmt(entity.center.x)}" cy="{_fmt(entity.center.y)}" '
                f'r="{_fmt(entity.radius)}"{dash}/>'
            )
        if isinstance(entity, ArcEntity):
            start_x, start_y = _arc_endpoint(entity, entity.start_angle_deg)
            end_x, end_y = _arc_endpoint(entity, entity.end_angle_deg)
            span = (entity.end_angle_deg - entity.start_angle_deg) % 360.0
            large_arc = 1 if span > 180.0 else 0
            return (
                f'<path id="{entity_id}" d="M {_fmt(start_x)} {_fmt(start_y)} '
                f'A {_fmt(entity.radius)} {_fmt(entity.radius)} 0 {large_arc} 1 '
                f'{_fmt(end_x)} {_fmt(end_y)}"{dash}/>'
            )
        if isinstance(entity, PolylineEntity):
            points = " ".join(f"{_fmt(point.x)},{_fmt(point.y)}" for point in entity.points)
            tag = "polygon" if entity.closed else "polyline"
            return f'<{tag} id="{entity_id}" points="{points}"{dash}/>'
        raise TypeError(f"unsupported CAD entity: {type(entity).__name__}")
