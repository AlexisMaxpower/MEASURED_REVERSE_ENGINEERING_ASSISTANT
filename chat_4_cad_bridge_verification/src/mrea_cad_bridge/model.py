from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TypeAlias


def _require_finite(name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


@dataclass(frozen=True, slots=True)
class Point2D:
    x: float
    y: float

    def __post_init__(self) -> None:
        _require_finite("x", self.x)
        _require_finite("y", self.y)


@dataclass(frozen=True, slots=True)
class PointEntity:
    entity_id: str
    point: Point2D
    construction: bool = False


@dataclass(frozen=True, slots=True)
class LineEntity:
    entity_id: str
    start: Point2D
    end: Point2D
    construction: bool = False


@dataclass(frozen=True, slots=True)
class CircleEntity:
    entity_id: str
    center: Point2D
    radius: float
    construction: bool = False

    def __post_init__(self) -> None:
        _require_finite("radius", self.radius)
        if self.radius <= 0:
            raise ValueError("radius must be > 0")


@dataclass(frozen=True, slots=True)
class ArcEntity:
    entity_id: str
    center: Point2D
    radius: float
    start_angle_deg: float
    end_angle_deg: float
    construction: bool = False

    def __post_init__(self) -> None:
        _require_finite("radius", self.radius)
        _require_finite("start_angle_deg", self.start_angle_deg)
        _require_finite("end_angle_deg", self.end_angle_deg)
        if self.radius <= 0:
            raise ValueError("radius must be > 0")


@dataclass(frozen=True, slots=True)
class PolylineEntity:
    entity_id: str
    points: tuple[Point2D, ...]
    closed: bool = False
    construction: bool = False

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("polyline requires at least two points")


CadEntity: TypeAlias = PointEntity | LineEntity | CircleEntity | ArcEntity | PolylineEntity


@dataclass(frozen=True, slots=True)
class CadSketch:
    entities: tuple[CadEntity, ...]
    units: str = "mm"

    def __post_init__(self) -> None:
        if self.units != "mm":
            raise ValueError("Chat 4 internal baseline currently supports millimetres only")
        ids = [entity.entity_id for entity in self.entities]
        if len(ids) != len(set(ids)):
            raise ValueError("entity_id values must be unique")

    def deterministic_entities(self) -> tuple[CadEntity, ...]:
        return tuple(sorted(self.entities, key=lambda entity: entity.entity_id))
