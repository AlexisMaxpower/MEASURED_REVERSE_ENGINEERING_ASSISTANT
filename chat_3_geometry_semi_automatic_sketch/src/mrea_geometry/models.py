from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

PrimitiveKind = Literal["POINT", "LINE", "CIRCLE", "ARC"]
ConstraintKind = Literal[
    "HORIZONTAL",
    "VERTICAL",
    "PARALLEL",
    "PERPENDICULAR",
    "CONCENTRIC",
    "EQUAL",
]


@dataclass(frozen=True, order=True, slots=True)
class Point2D:
    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {"x": float(self.x), "y": float(self.y)}


@dataclass(frozen=True, slots=True)
class PointEntity:
    entity_id: str
    point: Point2D
    feature_id: str | None = None
    source: str = "VISION_DETECTED"
    confidence: float | None = None

    @property
    def kind(self) -> PrimitiveKind:
        return "POINT"

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "point": self.point.to_dict(),
            "feature_id": self.feature_id,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class Line:
    entity_id: str
    start: Point2D
    end: Point2D
    feature_id: str | None = None
    source: str = "VISION_DETECTED"
    confidence: float | None = None

    @property
    def kind(self) -> PrimitiveKind:
        return "LINE"

    @property
    def length(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return (dx * dx + dy * dy) ** 0.5

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "feature_id": self.feature_id,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class Circle:
    entity_id: str
    center: Point2D
    radius: float
    feature_id: str | None = None
    source: str = "VISION_DETECTED"
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError("circle radius must be positive")

    @property
    def kind(self) -> PrimitiveKind:
        return "CIRCLE"

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "center": self.center.to_dict(),
            "radius": float(self.radius),
            "feature_id": self.feature_id,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class Arc:
    entity_id: str
    center: Point2D
    radius: float
    start_angle_deg: float
    end_angle_deg: float
    feature_id: str | None = None
    source: str = "VISION_DETECTED"
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError("arc radius must be positive")

    @property
    def kind(self) -> PrimitiveKind:
        return "ARC"

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "center": self.center.to_dict(),
            "radius": float(self.radius),
            "start_angle_deg": float(self.start_angle_deg),
            "end_angle_deg": float(self.end_angle_deg),
            "feature_id": self.feature_id,
            "source": self.source,
            "confidence": self.confidence,
        }


GeometryPrimitive = Union[PointEntity, Line, Circle, Arc]


@dataclass(frozen=True, slots=True)
class AnchorRef:
    """Anchor normalized into the Chat 3 geometry coordinate system."""

    anchor_id: str
    point: Point2D
    feature_id: str | None = None


@dataclass(frozen=True, slots=True)
class MeasurementRef:
    """Contract-neutral normalized measurement consumed by Chat 3 internally."""

    measurement_id: str
    measurement_type: str
    value: float
    unit: str
    verified: bool
    source: str
    anchors: tuple[AnchorRef, ...]

    def __post_init__(self) -> None:
        if not self.measurement_id.strip():
            raise ValueError("measurement_id is required")
        if not self.anchors:
            raise ValueError("at least one normalized anchor is required")


@dataclass(frozen=True, slots=True)
class ConstraintCandidate:
    constraint_id: str
    kind: ConstraintKind
    entity_ids: tuple[str, ...]
    inferred: bool = True
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "constraint_id": self.constraint_id,
            "kind": self.kind,
            "entity_ids": list(self.entity_ids),
            "inferred": self.inferred,
            "confidence": float(self.confidence),
        }


@dataclass(frozen=True, slots=True)
class DimensionBinding:
    dimension_id: str
    measurement_id: str
    measurement_type: str
    value: float
    unit: str
    verified: bool
    source: str
    target_entity_ids: tuple[str, ...]
    geometry_estimate: float | None

    def to_dict(self) -> dict:
        return {
            "dimension_id": self.dimension_id,
            "measurement_id": self.measurement_id,
            "measurement_type": self.measurement_type,
            "value": float(self.value),
            "unit": self.unit,
            "verified": self.verified,
            "source": self.source,
            "target_entity_ids": list(self.target_entity_ids),
            "geometry_estimate": (
                None if self.geometry_estimate is None else float(self.geometry_estimate)
            ),
        }


@dataclass(frozen=True, slots=True)
class UnresolvedBinding:
    measurement_id: str
    code: str
    anchor_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "measurement_id": self.measurement_id,
            "code": self.code,
            "anchor_ids": list(self.anchor_ids),
        }


@dataclass(frozen=True, slots=True)
class GeometryConflict:
    conflict_id: str
    code: str
    measurement_id: str
    measured_value: float
    derived_value: float
    delta: float
    tolerance: float

    def to_dict(self) -> dict:
        return {
            "conflict_id": self.conflict_id,
            "code": self.code,
            "measurement_id": self.measurement_id,
            "measured_value": float(self.measured_value),
            "derived_value": float(self.derived_value),
            "delta": float(self.delta),
            "tolerance": float(self.tolerance),
        }


@dataclass(frozen=True, slots=True)
class GeometryDraft:
    """Internal deterministic output. This is not canonical SketchPackage v1."""

    graph: object
    entities: tuple[GeometryPrimitive, ...] = field(default_factory=tuple)
    constraints: tuple[ConstraintCandidate, ...] = field(default_factory=tuple)
    dimensions: tuple[DimensionBinding, ...] = field(default_factory=tuple)
    unresolved: tuple[UnresolvedBinding, ...] = field(default_factory=tuple)
    conflicts: tuple[GeometryConflict, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "internal_format": "MREA_CHAT3_GEOMETRY_DRAFT_V1",
            "graph": self.graph.to_dict(),
            "entities": [entity.to_dict() for entity in self.entities],
            "constraints": [constraint.to_dict() for constraint in self.constraints],
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "unresolved": [item.to_dict() for item in self.unresolved],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }
