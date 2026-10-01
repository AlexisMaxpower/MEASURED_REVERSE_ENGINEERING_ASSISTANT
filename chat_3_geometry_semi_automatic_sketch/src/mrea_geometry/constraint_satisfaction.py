from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin

from .models import Arc, Circle, ConstraintCandidate, GeometryPrimitive, Line, Point2D, PointEntity


@dataclass(frozen=True, slots=True)
class ConstraintSatisfaction:
    """Read-only diagnostic for one constraint candidate against current geometry."""

    constraint_id: str
    kind: str
    entity_ids: tuple[str, ...]
    satisfied: bool
    residual: float
    tolerance: float
    unit: str


class ConstraintSatisfactionAnalyzer:
    """Measure whether a candidate relation is still satisfied by current geometry.

    The analyzer never moves entities. Linear/topological residuals are reported in mm;
    angular relations use a dimensionless normalized residual (sin/cos error).
    """

    def __init__(
        self,
        *,
        linear_tolerance: float = 0.05,
        angular_tolerance: float = 1e-3,
    ) -> None:
        if linear_tolerance < 0 or angular_tolerance < 0:
            raise ValueError("constraint satisfaction tolerances must be non-negative")
        self.linear_tolerance = linear_tolerance
        self.angular_tolerance = angular_tolerance

    def analyze(
        self,
        candidate: ConstraintCandidate,
        entities: dict[str, GeometryPrimitive],
    ) -> ConstraintSatisfaction:
        refs = tuple(entities[entity_id] for entity_id in candidate.entity_ids)
        residual, tolerance, unit = self._residual(candidate.kind, refs)
        return ConstraintSatisfaction(
            constraint_id=candidate.constraint_id,
            kind=candidate.kind,
            entity_ids=candidate.entity_ids,
            satisfied=residual <= tolerance,
            residual=residual,
            tolerance=tolerance,
            unit=unit,
        )

    def _residual(
        self,
        kind: str,
        refs: tuple[GeometryPrimitive, ...],
    ) -> tuple[float, float, str]:
        if kind == "HORIZONTAL" and len(refs) == 1 and isinstance(refs[0], Line):
            return self._axis_residual(refs[0], horizontal=True)
        if kind == "VERTICAL" and len(refs) == 1 and isinstance(refs[0], Line):
            return self._axis_residual(refs[0], horizontal=False)
        if kind in {"PARALLEL", "PERPENDICULAR"} and len(refs) == 2:
            if isinstance(refs[0], Line) and isinstance(refs[1], Line):
                return self._line_relation_residual(refs[0], refs[1], kind)
        if kind == "EQUAL" and len(refs) == 2:
            residual = self._equal_residual(refs[0], refs[1])
            return residual, self.linear_tolerance, "mm"
        if kind == "CONCENTRIC" and len(refs) == 2:
            if isinstance(refs[0], (Circle, Arc)) and isinstance(refs[1], (Circle, Arc)):
                return (
                    hypot(refs[0].center.x - refs[1].center.x, refs[0].center.y - refs[1].center.y),
                    self.linear_tolerance,
                    "mm",
                )
        if kind == "COINCIDENT" and len(refs) == 2:
            return self._coincident_residual(refs[0], refs[1]), self.linear_tolerance, "mm"
        if kind == "TANGENT" and len(refs) == 2:
            return self._tangent_residual(refs[0], refs[1]), self.linear_tolerance, "mm"
        if kind == "SYMMETRIC" and len(refs) == 3 and isinstance(refs[2], Line):
            return self._symmetric_residual(refs[0], refs[1], refs[2]), self.linear_tolerance, "mm"
        return float("inf"), self.linear_tolerance, "mm"

    def _axis_residual(self, line: Line, *, horizontal: bool) -> tuple[float, float, str]:
        dx = line.end.x - line.start.x
        dy = line.end.y - line.start.y
        length = hypot(dx, dy)
        if length == 0:
            return float("inf"), self.angular_tolerance, "normalized"
        residual = abs(dy if horizontal else dx) / length
        return residual, self.angular_tolerance, "normalized"

    def _line_relation_residual(
        self,
        first: Line,
        second: Line,
        kind: str,
    ) -> tuple[float, float, str]:
        ax, ay = first.end.x - first.start.x, first.end.y - first.start.y
        bx, by = second.end.x - second.start.x, second.end.y - second.start.y
        denominator = hypot(ax, ay) * hypot(bx, by)
        if denominator == 0:
            return float("inf"), self.angular_tolerance, "normalized"
        if kind == "PARALLEL":
            residual = abs(ax * by - ay * bx) / denominator
        else:
            residual = abs(ax * bx + ay * by) / denominator
        return residual, self.angular_tolerance, "normalized"

    @staticmethod
    def _equal_residual(first: GeometryPrimitive, second: GeometryPrimitive) -> float:
        if isinstance(first, Line) and isinstance(second, Line):
            return abs(first.length - second.length)
        if isinstance(first, (Circle, Arc)) and isinstance(second, (Circle, Arc)):
            return abs(first.radius - second.radius)
        return float("inf")

    def _coincident_residual(self, first: GeometryPrimitive, second: GeometryPrimitive) -> float:
        values = [
            self._distance_to_primitive(point, second)
            for point in self._contact_points(first)
        ]
        values.extend(
            self._distance_to_primitive(point, first)
            for point in self._contact_points(second)
        )
        return min(values, default=float("inf"))

    def _tangent_residual(self, first: GeometryPrimitive, second: GeometryPrimitive) -> float:
        if isinstance(first, Line) and isinstance(second, (Circle, Arc)):
            return self._line_round_tangent_residual(first, second)
        if isinstance(second, Line) and isinstance(first, (Circle, Arc)):
            return self._line_round_tangent_residual(second, first)
        if isinstance(first, (Circle, Arc)) and isinstance(second, (Circle, Arc)):
            return self._round_round_tangent_residual(first, second)
        return float("inf")

    def _line_round_tangent_residual(self, line: Line, round_entity: Circle | Arc) -> float:
        dx = line.end.x - line.start.x
        dy = line.end.y - line.start.y
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return float("inf")
        parameter = (
            (round_entity.center.x - line.start.x) * dx
            + (round_entity.center.y - line.start.y) * dy
        ) / length_sq
        if parameter < 0.0 or parameter > 1.0:
            return float("inf")
        nearest = Point2D(line.start.x + parameter * dx, line.start.y + parameter * dy)
        if isinstance(round_entity, Arc) and not self._point_on_arc(nearest, round_entity):
            return float("inf")
        distance = hypot(nearest.x - round_entity.center.x, nearest.y - round_entity.center.y)
        return abs(distance - round_entity.radius)

    def _round_round_tangent_residual(
        self,
        first: Circle | Arc,
        second: Circle | Arc,
    ) -> float:
        dx = second.center.x - first.center.x
        dy = second.center.y - first.center.y
        distance = hypot(dx, dy)
        if distance == 0:
            return float("inf")
        external_error = abs(distance - (first.radius + second.radius))
        internal_error = abs(distance - abs(first.radius - second.radius))
        internal = internal_error < external_error
        residual = internal_error if internal else external_error

        ux, uy = dx / distance, dy / distance
        if internal and second.radius > first.radius:
            tangent = Point2D(first.center.x - ux * first.radius, first.center.y - uy * first.radius)
        else:
            tangent = Point2D(first.center.x + ux * first.radius, first.center.y + uy * first.radius)
        if isinstance(first, Arc) and not self._point_on_arc(tangent, first):
            return float("inf")
        if isinstance(second, Arc) and not self._point_on_arc(tangent, second):
            return float("inf")
        return residual

    def _symmetric_residual(
        self,
        first: GeometryPrimitive,
        second: GeometryPrimitive,
        axis: Line,
    ) -> float:
        if isinstance(first, PointEntity) and isinstance(second, PointEntity):
            reflected = self._reflect(first.point, axis)
            return hypot(reflected.x - second.point.x, reflected.y - second.point.y)
        if isinstance(first, Circle) and isinstance(second, Circle):
            reflected = self._reflect(first.center, axis)
            center_error = hypot(reflected.x - second.center.x, reflected.y - second.center.y)
            return max(center_error, abs(first.radius - second.radius))
        return float("inf")

    @staticmethod
    def _reflect(point: Point2D, axis: Line) -> Point2D:
        dx = axis.end.x - axis.start.x
        dy = axis.end.y - axis.start.y
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return Point2D(float("inf"), float("inf"))
        parameter = (
            (point.x - axis.start.x) * dx + (point.y - axis.start.y) * dy
        ) / length_sq
        foot_x = axis.start.x + parameter * dx
        foot_y = axis.start.y + parameter * dy
        return Point2D(2.0 * foot_x - point.x, 2.0 * foot_y - point.y)

    @staticmethod
    def _contact_points(entity: GeometryPrimitive) -> tuple[Point2D, ...]:
        if isinstance(entity, PointEntity):
            return (entity.point,)
        if isinstance(entity, Line):
            return (entity.start, entity.end)
        if isinstance(entity, Arc):
            return (
                Point2D(
                    entity.center.x + entity.radius * cos(radians(entity.start_angle_deg)),
                    entity.center.y + entity.radius * sin(radians(entity.start_angle_deg)),
                ),
                Point2D(
                    entity.center.x + entity.radius * cos(radians(entity.end_angle_deg)),
                    entity.center.y + entity.radius * sin(radians(entity.end_angle_deg)),
                ),
            )
        return ()

    def _distance_to_primitive(self, point: Point2D, entity: GeometryPrimitive) -> float:
        if isinstance(entity, PointEntity):
            return hypot(point.x - entity.point.x, point.y - entity.point.y)
        if isinstance(entity, Line):
            return self._point_segment_distance(point, entity)
        radial = hypot(point.x - entity.center.x, point.y - entity.center.y)
        radial_error = abs(radial - entity.radius)
        if isinstance(entity, Circle):
            return radial_error
        if self._point_on_arc(point, entity):
            return radial_error
        return float("inf")

    @staticmethod
    def _point_segment_distance(point: Point2D, line: Line) -> float:
        dx = line.end.x - line.start.x
        dy = line.end.y - line.start.y
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return hypot(point.x - line.start.x, point.y - line.start.y)
        parameter = ((point.x - line.start.x) * dx + (point.y - line.start.y) * dy) / length_sq
        parameter = max(0.0, min(1.0, parameter))
        nearest_x = line.start.x + parameter * dx
        nearest_y = line.start.y + parameter * dy
        return hypot(point.x - nearest_x, point.y - nearest_y)

    @staticmethod
    def _point_on_arc(point: Point2D, arc: Arc) -> bool:
        angle = degrees(atan2(point.y - arc.center.y, point.x - arc.center.x)) % 360.0
        start = arc.start_angle_deg % 360.0
        end = arc.end_angle_deg % 360.0
        if start <= end:
            return start <= angle <= end
        return angle >= start or angle <= end
