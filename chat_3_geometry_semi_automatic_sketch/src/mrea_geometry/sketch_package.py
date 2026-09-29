from __future__ import annotations

from math import atan2, pi

from .contracts import CanonicalGeometryInput
from .models import Arc, Circle, DimensionBinding, GeometryDraft, Line, PointEntity


class SketchPackageBuilder:
    """Build Integrator-owned SketchPackage v1 without redefining its schema."""

    def build(
        self,
        draft: GeometryDraft,
        context: CanonicalGeometryInput,
        *,
        sketch_package_id: str,
    ) -> dict:
        entities = self._ordered_entities(draft)
        dimensions = sorted(
            (self._dimension(item, draft) for item in draft.dimensions),
            key=self._dimension_sort_key,
        )
        unresolved = [
            {
                "unresolved_id": f"U-{item.measurement_id}",
                "code": item.code,
                "message": "Measurement anchors could not be resolved to unambiguous geometry.",
                "measurement_ids": [item.measurement_id],
            }
            for item in sorted(draft.unresolved, key=lambda value: value.measurement_id)
        ]
        unresolved.extend(
            {
                "unresolved_id": f"U-{item.conflict_id}",
                "code": item.code,
                "message": (
                    f"Verified value {item.measured_value} conflicts with derived geometry "
                    f"{item.derived_value}; verified measurement was preserved."
                ),
                "measurement_ids": [item.measurement_id],
            }
            for item in sorted(draft.conflicts, key=lambda value: value.conflict_id)
        )

        return {
            "schema_version": "mrea.sketch-package.v1",
            "sketch_package_id": sketch_package_id,
            "project_id": context.project_id,
            "part_id": context.part_id,
            "view_id": context.view_id,
            "coordinate_system": context.coordinate_system,
            "entities": entities,
            # Phase 2 publishes no purely inferred constraints. They remain internal
            # candidates until a later acceptance rule promotes them.
            "constraints": [],
            "dimensions": dimensions,
            "unresolved": unresolved,
            "source_view_ids": list(context.source_view_ids),
        }

    def _ordered_entities(self, draft: GeometryDraft) -> list[dict]:
        lines = [item for item in draft.entities if isinstance(item, Line)]
        circles = [item for item in draft.entities if isinstance(item, Circle)]
        arcs = [item for item in draft.entities if isinstance(item, Arc)]
        points = [item for item in draft.entities if isinstance(item, PointEntity)]

        ordered: list = []
        if lines:
            midpoints = [((item.start.x + item.end.x) / 2, (item.start.y + item.end.y) / 2) for item in lines]
            center_x = sum(value[0] for value in midpoints) / len(midpoints)
            center_y = sum(value[1] for value in midpoints) / len(midpoints)

            def contour_key(line: Line) -> tuple[float, str]:
                mid_x = (line.start.x + line.end.x) / 2
                mid_y = (line.start.y + line.end.y) / 2
                phase = (atan2(mid_y - center_y, mid_x - center_x) + pi / 2) % (2 * pi)
                return phase, line.entity_id

            ordered.extend(sorted(lines, key=contour_key))
        ordered.extend(sorted(circles, key=lambda item: (item.center.x, item.center.y, item.entity_id)))
        ordered.extend(
            sorted(
                arcs,
                key=lambda item: (
                    item.center.x,
                    item.center.y,
                    item.radius,
                    item.start_angle_deg,
                    item.end_angle_deg,
                    item.entity_id,
                ),
            )
        )
        ordered.extend(sorted(points, key=lambda item: (item.point.x, item.point.y, item.entity_id)))
        return [self._entity(item) for item in ordered]

    @staticmethod
    def _entity(entity) -> dict:
        base = {
            "entity_id": entity.entity_id,
            "type": entity.kind,
            "provenance": entity.source,
        }
        if entity.confidence is not None:
            base["confidence"] = float(entity.confidence)
        if isinstance(entity, PointEntity):
            base["point"] = entity.point.to_dict()
        elif isinstance(entity, Line):
            base["start"] = entity.start.to_dict()
            base["end"] = entity.end.to_dict()
        elif isinstance(entity, Circle):
            base["center"] = entity.center.to_dict()
            base["radius"] = float(entity.radius)
        elif isinstance(entity, Arc):
            base["center"] = entity.center.to_dict()
            base["radius"] = float(entity.radius)
            base["start_angle_deg"] = float(entity.start_angle_deg)
            base["end_angle_deg"] = float(entity.end_angle_deg)
        return base

    def _dimension(self, item: DimensionBinding, draft: GeometryDraft) -> dict:
        return {
            "dimension_id": self._dimension_id(item.measurement_id),
            "measurement_id": item.measurement_id,
            "type": self._dimension_type(item.measurement_type),
            "value": float(item.value),
            "unit": item.unit,
            "entity_ids": list(self._canonical_dimension_entities(item, draft)),
            "verified": item.verified,
            "provenance": item.source,
            "_measurement_type": item.measurement_type,
        }

    @staticmethod
    def _dimension_id(measurement_id: str) -> str:
        if measurement_id.startswith("M-"):
            return f"D-{measurement_id[2:]}"
        return f"D-{measurement_id}"

    @staticmethod
    def _dimension_type(measurement_type: str) -> str:
        if measurement_type in {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"}:
            return "DIAMETER"
        if measurement_type == "RADIUS":
            return "RADIUS"
        if measurement_type == "ANGLE":
            return "ANGLE"
        return "DISTANCE"

    @staticmethod
    def _canonical_dimension_entities(
        item: DimensionBinding,
        draft: GeometryDraft,
    ) -> tuple[str, ...]:
        if item.measurement_type in {
            "LINEAR_EXTERNAL",
            "LINEAR_INTERNAL",
            "THICKNESS",
            "SLOT_WIDTH",
        }:
            candidates = sorted(
                entity.entity_id
                for entity in draft.entities
                if isinstance(entity, Line) and abs(entity.length - item.value) <= 1e-6
            )
            if candidates:
                return (candidates[0],)
        return item.target_entity_ids

    @staticmethod
    def _dimension_sort_key(item: dict) -> tuple[int, int, str]:
        measurement_type = item.pop("_measurement_type")
        if measurement_type in {"LINEAR_EXTERNAL", "LINEAR_INTERNAL", "THICKNESS", "SLOT_WIDTH"}:
            entity_id = item["entity_ids"][0] if item["entity_ids"] else ""
            orientation = 0 if "BOTTOM" in entity_id or "TOP" in entity_id else 1
            return 10, orientation, item["dimension_id"]
        if measurement_type in {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"}:
            return 20, 0, item["dimension_id"]
        if measurement_type == "RADIUS":
            return 30, 0, item["dimension_id"]
        if measurement_type == "ANGLE":
            return 40, 0, item["dimension_id"]
        if measurement_type == "CENTER_DISTANCE":
            return 50, 0, item["dimension_id"]
        return 60, 0, item["dimension_id"]
