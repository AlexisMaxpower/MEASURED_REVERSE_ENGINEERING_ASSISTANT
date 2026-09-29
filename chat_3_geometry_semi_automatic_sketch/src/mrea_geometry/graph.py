from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin

from .models import Arc, GeometryPrimitive, Line, Point2D, PointEntity


def _point_key(point: Point2D, precision: int = 9) -> tuple[float, float]:
    return round(point.x, precision), round(point.y, precision)


def _arc_endpoint(arc: Arc, angle_deg: float) -> Point2D:
    angle = radians(angle_deg)
    return Point2D(
        arc.center.x + arc.radius * cos(angle),
        arc.center.y + arc.radius * sin(angle),
    )


@dataclass(frozen=True, slots=True)
class GeometryGraph:
    entity_ids: tuple[str, ...]
    adjacency: dict[str, tuple[str, ...]]

    @classmethod
    def build(cls, entities: tuple[GeometryPrimitive, ...]) -> "GeometryGraph":
        entity_ids = [entity.entity_id for entity in entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("entity_id values must be unique")

        incidence: dict[tuple[float, float], list[str]] = {}
        for entity in entities:
            points: tuple[Point2D, ...] = ()
            if isinstance(entity, PointEntity):
                points = (entity.point,)
            elif isinstance(entity, Line):
                points = (entity.start, entity.end)
            elif isinstance(entity, Arc):
                points = (
                    _arc_endpoint(entity, entity.start_angle_deg),
                    _arc_endpoint(entity, entity.end_angle_deg),
                )
            for point in points:
                incidence.setdefault(_point_key(point), []).append(entity.entity_id)

        adjacency_sets = {entity_id: set() for entity_id in entity_ids}
        for attached_ids in incidence.values():
            unique_ids = sorted(set(attached_ids))
            for entity_id in unique_ids:
                adjacency_sets[entity_id].update(
                    other for other in unique_ids if other != entity_id
                )

        return cls(
            entity_ids=tuple(sorted(entity_ids)),
            adjacency={
                entity_id: tuple(sorted(adjacency_sets[entity_id]))
                for entity_id in sorted(adjacency_sets)
            },
        )

    def to_dict(self) -> dict:
        return {
            "entity_ids": list(self.entity_ids),
            "adjacency": {
                entity_id: list(neighbors)
                for entity_id, neighbors in self.adjacency.items()
            },
        }
