from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, isfinite, pi, radians, sin
from xml.sax.saxutils import escape, quoteattr


@dataclass(frozen=True, slots=True)
class ReferenceImageLayer:
    """Explicitly aligned clean-reference image for a Dimensioned View.

    Bounds are expressed in the same MAT_XY_MM coordinate system as SketchPackage.
    The renderer never guesses image registration from pixel dimensions.
    """

    href: str
    min_x_mm: float
    min_y_mm: float
    max_x_mm: float
    max_y_mm: float
    opacity: float = 0.35

    def __post_init__(self) -> None:
        if not self.href.strip():
            raise ValueError("reference image href is required")
        values = (self.min_x_mm, self.min_y_mm, self.max_x_mm, self.max_y_mm)
        if not all(isfinite(float(value)) for value in values):
            raise ValueError("reference image bounds must be finite")
        if self.max_x_mm <= self.min_x_mm or self.max_y_mm <= self.min_y_mm:
            raise ValueError("reference image bounds must have positive area")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("reference image opacity must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class DimensionedViewArtifact:
    """Slice-local visual artifact. This is not a shared wire contract."""

    svg: str
    width_px: int
    height_px: int
    sketch_package_id: str
    dimension_ids: tuple[str, ...]
    measurement_ids: tuple[str, ...]


class DimensionedViewRenderer:
    """Render deterministic SVG from a canonical SketchPackage v1.

    The renderer is deliberately read-only: verified dimensions/provenance are displayed,
    never recomputed or corrected. Optional reference imagery must arrive with explicit
    MAT_XY_MM bounds so image registration is not guessed.
    """

    def __init__(
        self,
        *,
        scale_px_per_mm: float = 8.0,
        padding_px: float = 48.0,
        dimension_gap_px: float = 22.0,
        min_width_px: int = 360,
        min_height_px: int = 260,
    ) -> None:
        if scale_px_per_mm <= 0 or not isfinite(scale_px_per_mm):
            raise ValueError("scale_px_per_mm must be a positive finite value")
        if padding_px < 0 or not isfinite(padding_px):
            raise ValueError("padding_px must be a non-negative finite value")
        if dimension_gap_px <= 0 or not isfinite(dimension_gap_px):
            raise ValueError("dimension_gap_px must be a positive finite value")
        self.scale_px_per_mm = float(scale_px_per_mm)
        self.padding_px = float(padding_px)
        self.dimension_gap_px = float(dimension_gap_px)
        self.min_width_px = int(min_width_px)
        self.min_height_px = int(min_height_px)

    def render(
        self,
        sketch_package: dict,
        *,
        reference_image: ReferenceImageLayer | None = None,
    ) -> DimensionedViewArtifact:
        self._validate_package(sketch_package)
        entities = self._entity_map(sketch_package)
        bounds = self._geometry_bounds(tuple(entities.values()))

        min_x, min_y, max_x, max_y = bounds
        geometry_width = max(max_x - min_x, 1.0)
        geometry_height = max(max_y - min_y, 1.0)

        dimensions = sorted(
            sketch_package.get("dimensions", []),
            key=lambda item: str(item["dimension_id"]),
        )
        unresolved = sorted(
            sketch_package.get("unresolved", []),
            key=lambda item: str(item["unresolved_id"]),
        )

        annotation_allowance = self.dimension_gap_px * max(len(dimensions), 2) + 32.0
        footer_lines = 2 + len(unresolved)
        footer_height = 22.0 * footer_lines + 20.0
        geometry_margin = self.padding_px + annotation_allowance

        width = max(
            self.min_width_px,
            int(round(geometry_width * self.scale_px_per_mm + 2 * geometry_margin)),
        )
        height = max(
            self.min_height_px,
            int(round(geometry_height * self.scale_px_per_mm + 2 * geometry_margin + footer_height)),
        )

        offset_x = geometry_margin
        offset_y = geometry_margin

        def project(point: tuple[float, float]) -> tuple[float, float]:
            x, y = point
            return (
                offset_x + (x - min_x) * self.scale_px_per_mm,
                offset_y + (max_y - y) * self.scale_px_per_mm,
            )

        center_px = project(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0))

        lines: list[str] = []
        lines.append(
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            'role="img" aria-label="MREA dimensioned view">'
        )
        lines.append(
            "<metadata>"
            + escape(
                "MREA Dimensioned View | sketch_package_id="
                + str(sketch_package["sketch_package_id"])
                + " | coordinate_system=MAT_XY_MM"
            )
            + "</metadata>"
        )
        lines.extend(self._defs())

        if reference_image is not None:
            x1, y1 = project((reference_image.min_x_mm, reference_image.max_y_mm))
            x2, y2 = project((reference_image.max_x_mm, reference_image.min_y_mm))
            lines.append(
                '<g id="clean-reference-layer">'
                '<image id="clean-reference" '
                f'href={quoteattr(reference_image.href)} '
                f'x="{self._fmt(x1)}" y="{self._fmt(y1)}" '
                f'width="{self._fmt(x2 - x1)}" height="{self._fmt(y2 - y1)}" '
                f'opacity="{self._fmt(reference_image.opacity)}" preserveAspectRatio="none"/>'
                "</g>"
            )

        lines.append('<g id="geometry-overlay" fill="none" stroke="currentColor">')
        for entity in self._ordered_entities(tuple(entities.values())):
            lines.append(self._render_entity(entity, project))
        lines.append("</g>")

        lines.append('<g id="dimension-overlay" fill="none" stroke="currentColor">')
        for lane, dimension in enumerate(dimensions):
            lines.extend(
                self._render_dimension(
                    dimension,
                    entities,
                    project=project,
                    center_px=center_px,
                    lane=lane,
                )
            )
        lines.append("</g>")

        footer_y = offset_y + geometry_height * self.scale_px_per_mm + annotation_allowance + 18.0
        lines.extend(
            self._render_footer(
                sketch_package,
                unresolved=unresolved,
                y=footer_y,
            )
        )
        lines.append("</svg>")

        measurement_ids = tuple(
            str(item["measurement_id"])
            for item in dimensions
            if item.get("measurement_id") is not None
        )
        return DimensionedViewArtifact(
            svg="\n".join(lines) + "\n",
            width_px=width,
            height_px=height,
            sketch_package_id=str(sketch_package["sketch_package_id"]),
            dimension_ids=tuple(str(item["dimension_id"]) for item in dimensions),
            measurement_ids=measurement_ids,
        )

    @staticmethod
    def _defs() -> list[str]:
        return [
            "<defs>",
            '<marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse" markerUnits="strokeWidth">',
            '<path d="M 0 0 L 8 4 L 0 8 z" fill="currentColor"/>',
            "</marker>",
            "</defs>",
        ]

    @staticmethod
    def _validate_package(sketch_package: dict) -> None:
        if sketch_package.get("schema_version") != "mrea.sketch-package.v1":
            raise ValueError("DimensionedViewRenderer requires SketchPackage v1")
        if sketch_package.get("coordinate_system") != "MAT_XY_MM":
            raise ValueError("DimensionedViewRenderer requires MAT_XY_MM coordinates")
        if not str(sketch_package.get("sketch_package_id", "")).strip():
            raise ValueError("sketch_package_id is required")
        if not isinstance(sketch_package.get("entities"), list) or not sketch_package["entities"]:
            raise ValueError("at least one sketch entity is required")

    @staticmethod
    def _entity_map(sketch_package: dict) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for entity in sketch_package["entities"]:
            entity_id = str(entity.get("entity_id", ""))
            if not entity_id:
                raise ValueError("entity_id is required")
            if entity_id in result:
                raise ValueError(f"duplicate entity_id: {entity_id}")
            result[entity_id] = entity
        return result

    @classmethod
    def _geometry_bounds(cls, entities: tuple[dict, ...]) -> tuple[float, float, float, float]:
        points: list[tuple[float, float]] = []
        for entity in entities:
            kind = entity.get("type")
            if kind == "POINT":
                points.append(cls._point(entity["point"]))
            elif kind == "LINE":
                points.extend((cls._point(entity["start"]), cls._point(entity["end"])))
            elif kind in {"CIRCLE", "ARC"}:
                cx, cy = cls._point(entity["center"])
                radius = cls._number(entity["radius"], "radius")
                if radius <= 0:
                    raise ValueError("circle/arc radius must be positive")
                points.extend(((cx - radius, cy - radius), (cx + radius, cy + radius)))
            else:
                raise ValueError(f"unsupported sketch entity type: {kind!r}")
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _ordered_entities(entities: tuple[dict, ...]) -> tuple[dict, ...]:
        order = {"LINE": 0, "CIRCLE": 1, "ARC": 2, "POINT": 3}
        return tuple(
            sorted(
                entities,
                key=lambda item: (order.get(str(item.get("type")), 99), str(item["entity_id"])),
            )
        )

    def _render_entity(self, entity: dict, project) -> str:
        entity_id = str(entity["entity_id"])
        kind = str(entity["type"])
        provenance = str(entity.get("provenance", ""))
        confidence = entity.get("confidence")
        attrs = (
            f'data-entity-id={quoteattr(entity_id)} '
            f'data-provenance={quoteattr(provenance)}'
        )
        if confidence is not None:
            attrs += f' data-confidence="{self._fmt(self._number(confidence, "confidence"))}"'
        title = escape(
            f"{entity_id} | {provenance}"
            + ("" if confidence is None else f" | confidence={float(confidence):.3f}")
        )

        if kind == "POINT":
            x, y = project(self._point(entity["point"]))
            return (
                f'<circle class="geometry-point" {attrs} cx="{self._fmt(x)}" cy="{self._fmt(y)}" r="2.5">'
                f"<title>{title}</title></circle>"
            )
        if kind == "LINE":
            x1, y1 = project(self._point(entity["start"]))
            x2, y2 = project(self._point(entity["end"]))
            return (
                f'<line class="geometry-line" {attrs} x1="{self._fmt(x1)}" y1="{self._fmt(y1)}" '
                f'x2="{self._fmt(x2)}" y2="{self._fmt(y2)}"><title>{title}</title></line>'
            )
        if kind == "CIRCLE":
            cx, cy = project(self._point(entity["center"]))
            radius_px = self._number(entity["radius"], "radius") * self.scale_px_per_mm
            return (
                f'<circle class="geometry-circle" {attrs} cx="{self._fmt(cx)}" cy="{self._fmt(cy)}" '
                f'r="{self._fmt(radius_px)}"><title>{title}</title></circle>'
            )
        if kind == "ARC":
            cx_mm, cy_mm = self._point(entity["center"])
            radius = self._number(entity["radius"], "radius")
            start = self._number(entity["start_angle_deg"], "start_angle_deg")
            end = self._number(entity["end_angle_deg"], "end_angle_deg")
            start_point = (
                cx_mm + radius * cos(radians(start)),
                cy_mm + radius * sin(radians(start)),
            )
            end_point = (
                cx_mm + radius * cos(radians(end)),
                cy_mm + radius * sin(radians(end)),
            )
            x1, y1 = project(start_point)
            x2, y2 = project(end_point)
            delta = (end - start) % 360.0
            large_arc = 1 if delta > 180.0 else 0
            radius_px = radius * self.scale_px_per_mm
            path = (
                f"M {self._fmt(x1)} {self._fmt(y1)} "
                f"A {self._fmt(radius_px)} {self._fmt(radius_px)} 0 {large_arc} 0 "
                f"{self._fmt(x2)} {self._fmt(y2)}"
            )
            return (
                f'<path class="geometry-arc" {attrs} d={quoteattr(path)}><title>{title}</title></path>'
            )
        raise ValueError(f"unsupported sketch entity type: {kind!r}")

    def _render_dimension(
        self,
        dimension: dict,
        entities: dict[str, dict],
        *,
        project,
        center_px: tuple[float, float],
        lane: int,
    ) -> list[str]:
        dimension_id = str(dimension["dimension_id"])
        entity_ids = tuple(str(item) for item in dimension.get("entity_ids", []))
        missing = tuple(item for item in entity_ids if item not in entities)
        if not entity_ids:
            raise ValueError(f"dimension {dimension_id} has no entity_ids")
        if missing:
            raise ValueError(f"dimension {dimension_id} references missing entities: {missing}")

        kind = str(dimension["type"])
        value = self._number(dimension["value"], "dimension value")
        unit = str(dimension["unit"])
        measurement_id = dimension.get("measurement_id")
        provenance = str(dimension.get("provenance", ""))
        verified = bool(dimension.get("verified", False))
        label = f"{self._fmt_measurement(value)} {unit}"
        trace = " · ".join(
            item
            for item in (
                None if measurement_id is None else str(measurement_id),
                provenance or None,
                "VERIFIED" if verified else "UNVERIFIED",
            )
            if item is not None
        )
        lane_gap = self.dimension_gap_px * (lane + 1)

        if kind == "DISTANCE":
            p1, p2 = self._distance_points(entity_ids, entities)
            return self._linear_dimension_markup(
                dimension_id,
                p1,
                p2,
                label,
                trace,
                project=project,
                center_px=center_px,
                offset_px=lane_gap,
                measurement_id=measurement_id,
                provenance=provenance,
                verified=verified,
            )
        if kind == "DIAMETER":
            entity = entities[entity_ids[0]]
            if entity.get("type") != "CIRCLE":
                raise ValueError(f"diameter dimension {dimension_id} requires a CIRCLE")
            cx, cy = self._point(entity["center"])
            radius = self._number(entity["radius"], "radius")
            p1 = (cx - radius, cy)
            p2 = (cx + radius, cy)
            return self._linear_dimension_markup(
                dimension_id,
                p1,
                p2,
                "Ø" + label,
                trace,
                project=project,
                center_px=center_px,
                offset_px=lane_gap / 2.0,
                measurement_id=measurement_id,
                provenance=provenance,
                verified=verified,
            )
        if kind == "RADIUS":
            entity = entities[entity_ids[0]]
            if entity.get("type") not in {"CIRCLE", "ARC"}:
                raise ValueError(f"radius dimension {dimension_id} requires CIRCLE or ARC")
            cx, cy = self._point(entity["center"])
            radius = self._number(entity["radius"], "radius")
            endpoint = (
                cx + radius * cos(pi / 4.0),
                cy + radius * sin(pi / 4.0),
            )
            return self._leader_dimension_markup(
                dimension_id,
                (cx, cy),
                endpoint,
                "R" + label,
                trace,
                project=project,
                measurement_id=measurement_id,
                provenance=provenance,
                verified=verified,
            )
        if kind == "ANGLE":
            return self._angle_dimension_markup(
                dimension_id,
                entity_ids,
                entities,
                value=value,
                unit=unit,
                trace=trace,
                project=project,
                lane=lane,
                measurement_id=measurement_id,
                provenance=provenance,
                verified=verified,
            )
        raise ValueError(f"unsupported sketch dimension type: {kind!r}")

    def _distance_points(
        self,
        entity_ids: tuple[str, ...],
        entities: dict[str, dict],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        if len(entity_ids) == 1:
            entity = entities[entity_ids[0]]
            if entity.get("type") == "LINE":
                return self._point(entity["start"]), self._point(entity["end"])
            if entity.get("type") == "CIRCLE":
                center = self._point(entity["center"])
                radius = self._number(entity["radius"], "radius")
                return (center[0] - radius, center[1]), (center[0] + radius, center[1])
        if len(entity_ids) == 2:
            first = self._representative_point(entities[entity_ids[0]])
            second = self._representative_point(entities[entity_ids[1]])
            return first, second
        first = self._representative_point(entities[entity_ids[0]])
        second = self._representative_point(entities[entity_ids[-1]])
        return first, second

    @classmethod
    def _representative_point(cls, entity: dict) -> tuple[float, float]:
        kind = entity.get("type")
        if kind == "POINT":
            return cls._point(entity["point"])
        if kind == "LINE":
            start = cls._point(entity["start"])
            end = cls._point(entity["end"])
            return ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        if kind in {"CIRCLE", "ARC"}:
            return cls._point(entity["center"])
        raise ValueError(f"unsupported sketch entity type: {kind!r}")

    def _linear_dimension_markup(
        self,
        dimension_id: str,
        p1_model: tuple[float, float],
        p2_model: tuple[float, float],
        label: str,
        trace: str,
        *,
        project,
        center_px: tuple[float, float],
        offset_px: float,
        measurement_id,
        provenance: str,
        verified: bool,
    ) -> list[str]:
        p1 = project(p1_model)
        p2 = project(p2_model)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = hypot(dx, dy)
        if length <= 1e-12:
            raise ValueError(f"dimension {dimension_id} has coincident endpoints")
        normal = (-dy / length, dx / length)
        midpoint = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
        away = (midpoint[0] - center_px[0], midpoint[1] - center_px[1])
        if normal[0] * away[0] + normal[1] * away[1] < 0:
            normal = (-normal[0], -normal[1])
        q1 = (p1[0] + normal[0] * offset_px, p1[1] + normal[1] * offset_px)
        q2 = (p2[0] + normal[0] * offset_px, p2[1] + normal[1] * offset_px)
        label_point = (
            (q1[0] + q2[0]) / 2.0 + normal[0] * 10.0,
            (q1[1] + q2[1]) / 2.0 + normal[1] * 10.0,
        )
        attrs = self._dimension_data_attrs(
            dimension_id,
            measurement_id=measurement_id,
            provenance=provenance,
            verified=verified,
        )
        return [
            f'<g class="dimension" {attrs}>',
            f'<line class="extension-line" x1="{self._fmt(p1[0])}" y1="{self._fmt(p1[1])}" x2="{self._fmt(q1[0])}" y2="{self._fmt(q1[1])}"/>',
            f'<line class="extension-line" x1="{self._fmt(p2[0])}" y1="{self._fmt(p2[1])}" x2="{self._fmt(q2[0])}" y2="{self._fmt(q2[1])}"/>',
            f'<line class="dimension-line" x1="{self._fmt(q1[0])}" y1="{self._fmt(q1[1])}" x2="{self._fmt(q2[0])}" y2="{self._fmt(q2[1])}" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
            f'<text class="dimension-value" font-size="13" x="{self._fmt(label_point[0])}" y="{self._fmt(label_point[1])}" fill="currentColor" stroke="none" text-anchor="middle">{escape(label)}</text>',
            f'<text class="dimension-trace" font-size="9" x="{self._fmt(label_point[0])}" y="{self._fmt(label_point[1] + 13.0)}" fill="currentColor" stroke="none" text-anchor="middle">{escape(trace)}</text>',
            "</g>",
        ]

    def _leader_dimension_markup(
        self,
        dimension_id: str,
        p1_model: tuple[float, float],
        p2_model: tuple[float, float],
        label: str,
        trace: str,
        *,
        project,
        measurement_id,
        provenance: str,
        verified: bool,
    ) -> list[str]:
        p1 = project(p1_model)
        p2 = project(p2_model)
        attrs = self._dimension_data_attrs(
            dimension_id,
            measurement_id=measurement_id,
            provenance=provenance,
            verified=verified,
        )
        return [
            f'<g class="dimension" {attrs}>',
            f'<line class="dimension-line" x1="{self._fmt(p1[0])}" y1="{self._fmt(p1[1])}" x2="{self._fmt(p2[0])}" y2="{self._fmt(p2[1])}" marker-end="url(#arrow)"/>',
            f'<text class="dimension-value" font-size="13" x="{self._fmt(p2[0] + 8.0)}" y="{self._fmt(p2[1] - 6.0)}" fill="currentColor" stroke="none">{escape(label)}</text>',
            f'<text class="dimension-trace" font-size="9" x="{self._fmt(p2[0] + 8.0)}" y="{self._fmt(p2[1] + 7.0)}" fill="currentColor" stroke="none">{escape(trace)}</text>',
            "</g>",
        ]

    def _angle_dimension_markup(
        self,
        dimension_id: str,
        entity_ids: tuple[str, ...],
        entities: dict[str, dict],
        *,
        value: float,
        unit: str,
        trace: str,
        project,
        lane: int,
        measurement_id,
        provenance: str,
        verified: bool,
    ) -> list[str]:
        if len(entity_ids) < 2:
            raise ValueError(f"angle dimension {dimension_id} requires two LINE entities")
        first = entities[entity_ids[0]]
        second = entities[entity_ids[1]]
        if first.get("type") != "LINE" or second.get("type") != "LINE":
            raise ValueError(f"angle dimension {dimension_id} requires two LINE entities")
        vertex = self._line_intersection(first, second)
        if vertex is None:
            raise ValueError(f"angle dimension {dimension_id} uses parallel lines")
        vertex_px = project(vertex)
        a1 = self._line_angle(first)
        a2 = self._line_angle(second)
        delta = ((a2 - a1 + pi) % (2 * pi)) - pi
        if delta < 0:
            a1, a2 = a2, a1
            delta = -delta
        radius_px = 24.0 + lane * 5.0
        start = (vertex_px[0] + radius_px * cos(-a1), vertex_px[1] + radius_px * sin(-a1))
        end = (vertex_px[0] + radius_px * cos(-a2), vertex_px[1] + radius_px * sin(-a2))
        large_arc = 1 if delta > pi else 0
        sweep = 0
        path = (
            f"M {self._fmt(start[0])} {self._fmt(start[1])} "
            f"A {self._fmt(radius_px)} {self._fmt(radius_px)} 0 {large_arc} {sweep} "
            f"{self._fmt(end[0])} {self._fmt(end[1])}"
        )
        mid_angle = a1 + delta / 2.0
        text_point = (
            vertex_px[0] + (radius_px + 16.0) * cos(-mid_angle),
            vertex_px[1] + (radius_px + 16.0) * sin(-mid_angle),
        )
        attrs = self._dimension_data_attrs(
            dimension_id,
            measurement_id=measurement_id,
            provenance=provenance,
            verified=verified,
        )
        return [
            f'<g class="dimension" {attrs}>',
            f'<path class="dimension-line" d={quoteattr(path)} marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
            f'<text class="dimension-value" font-size="13" x="{self._fmt(text_point[0])}" y="{self._fmt(text_point[1])}" fill="currentColor" stroke="none" text-anchor="middle">{escape(self._fmt_measurement(value) + " " + unit)}</text>',
            f'<text class="dimension-trace" font-size="9" x="{self._fmt(text_point[0])}" y="{self._fmt(text_point[1] + 13.0)}" fill="currentColor" stroke="none" text-anchor="middle">{escape(trace)}</text>',
            "</g>",
        ]

    @classmethod
    def _line_intersection(cls, first: dict, second: dict) -> tuple[float, float] | None:
        x1, y1 = cls._point(first["start"])
        x2, y2 = cls._point(first["end"])
        x3, y3 = cls._point(second["start"])
        x4, y4 = cls._point(second["end"])
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denominator) <= 1e-12:
            return None
        determinant1 = x1 * y2 - y1 * x2
        determinant2 = x3 * y4 - y3 * x4
        x = (determinant1 * (x3 - x4) - (x1 - x2) * determinant2) / denominator
        y = (determinant1 * (y3 - y4) - (y1 - y2) * determinant2) / denominator
        return x, y

    @classmethod
    def _line_angle(cls, line: dict) -> float:
        start = cls._point(line["start"])
        end = cls._point(line["end"])
        return atan2(end[1] - start[1], end[0] - start[0])

    def _render_footer(self, sketch_package: dict, *, unresolved: list[dict], y: float) -> list[str]:
        entity_provenance = sorted(
            {
                str(item.get("provenance", "UNKNOWN"))
                for item in sketch_package.get("entities", [])
            }
        )
        confidence_values = sorted(
            float(item["confidence"])
            for item in sketch_package.get("entities", [])
            if item.get("confidence") is not None
        )
        if confidence_values:
            confidence_text = (
                f"confidence {confidence_values[0]:.3f}–{confidence_values[-1]:.3f}"
                if confidence_values[0] != confidence_values[-1]
                else f"confidence {confidence_values[0]:.3f}"
            )
        else:
            confidence_text = "confidence n/a"
        dimension_provenance = sorted(
            {
                str(item.get("provenance", "UNKNOWN"))
                for item in sketch_package.get("dimensions", [])
            }
        )
        lines = ['<g id="traceability-footer" fill="currentColor" stroke="none">']
        lines.append(
            f'<text font-size="11" x="16" y="{self._fmt(y)}">Geometry: {escape(", ".join(entity_provenance))} · {escape(confidence_text)}</text>'
        )
        lines.append(
            f'<text font-size="11" x="16" y="{self._fmt(y + 20.0)}">Dimensions: {escape(", ".join(dimension_provenance) or "none")} · verified state preserved from SketchPackage</text>'
        )
        for index, item in enumerate(unresolved):
            text = f"UNRESOLVED {item['unresolved_id']}: {item['code']}"
            lines.append(
                f'<text class="unresolved-item" font-size="11" x="16" y="{self._fmt(y + 40.0 + 20.0 * index)}">{escape(text)}</text>'
            )
        lines.append("</g>")
        return lines

    @staticmethod
    def _dimension_data_attrs(
        dimension_id: str,
        *,
        measurement_id,
        provenance: str,
        verified: bool,
    ) -> str:
        attrs = [
            f'data-dimension-id={quoteattr(dimension_id)}',
            f'data-provenance={quoteattr(provenance)}',
            f'data-verified={quoteattr("true" if verified else "false")}',
        ]
        if measurement_id is not None:
            attrs.append(f'data-measurement-id={quoteattr(str(measurement_id))}')
        return " ".join(attrs)

    @classmethod
    def _point(cls, value: dict) -> tuple[float, float]:
        return cls._number(value["x"], "x"), cls._number(value["y"], "y")

    @staticmethod
    def _number(value, name: str) -> float:
        result = float(value)
        if not isfinite(result):
            raise ValueError(f"{name} must be finite")
        return result

    @staticmethod
    def _fmt(value: float) -> str:
        rounded = round(float(value), 6)
        if abs(rounded) < 0.0000005:
            rounded = 0.0
        text = f"{rounded:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"

    @staticmethod
    def _fmt_measurement(value: float) -> str:
        text = f"{float(value):.6f}".rstrip("0").rstrip(".")
        return text if text else "0"
