from __future__ import annotations

from itertools import combinations
from math import atan2, cos, degrees, hypot, isclose, radians, sin

from .graph import GeometryGraph
from .models import (
    Arc,
    AnchorRef,
    Circle,
    ConstraintCandidate,
    DimensionBinding,
    GeometryConflict,
    GeometryDraft,
    GeometryPrimitive,
    Line,
    MeasurementRef,
    Point2D,
    PointEntity,
    UnresolvedBinding,
)


def _point_segment_distance(point: Point2D, line: Line) -> float:
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return hypot(point.x - line.start.x, point.y - line.start.y)
    t = ((point.x - line.start.x) * dx + (point.y - line.start.y) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    nearest_x = line.start.x + t * dx
    nearest_y = line.start.y + t * dy
    return hypot(point.x - nearest_x, point.y - nearest_y)


def _normalized_angle(angle: float) -> float:
    return angle % 360.0


def _angle_on_arc(angle: float, start: float, end: float) -> bool:
    angle = _normalized_angle(angle)
    start = _normalized_angle(start)
    end = _normalized_angle(end)
    if start <= end:
        return start <= angle <= end
    return angle >= start or angle <= end


def _distance_to_primitive(point: Point2D, entity: GeometryPrimitive) -> float:
    if isinstance(entity, PointEntity):
        return hypot(point.x - entity.point.x, point.y - entity.point.y)
    if isinstance(entity, Line):
        return _point_segment_distance(point, entity)
    radial = hypot(point.x - entity.center.x, point.y - entity.center.y)
    radial_error = abs(radial - entity.radius)
    if isinstance(entity, Circle):
        return radial_error
    angle = degrees(atan2(point.y - entity.center.y, point.x - entity.center.x))
    if _angle_on_arc(angle, entity.start_angle_deg, entity.end_angle_deg):
        return radial_error
    return float("inf")


class AnchorEntityMatcher:
    def __init__(self, *, max_distance: float = 0.75, ambiguity_epsilon: float = 1e-9) -> None:
        if max_distance < 0:
            raise ValueError("max_distance must be non-negative")
        self.max_distance = max_distance
        self.ambiguity_epsilon = ambiguity_epsilon

    def match_anchor(
        self,
        anchor: AnchorRef,
        entities: tuple[GeometryPrimitive, ...],
    ) -> str | None:
        if anchor.feature_id:
            feature_matches = sorted(
                entity.entity_id
                for entity in entities
                if getattr(entity, "feature_id", None) == anchor.feature_id
            )
            if len(feature_matches) == 1:
                return feature_matches[0]
            if len(feature_matches) > 1:
                return None
        return self.match(anchor.point, entities)

    def match(self, point: Point2D, entities: tuple[GeometryPrimitive, ...]) -> str | None:
        ranked = sorted(
            ((_distance_to_primitive(point, entity), entity.entity_id) for entity in entities),
            key=lambda item: (item[0], item[1]),
        )
        if not ranked or ranked[0][0] > self.max_distance:
            return None
        if len(ranked) > 1 and abs(ranked[1][0] - ranked[0][0]) <= self.ambiguity_epsilon:
            return None
        return ranked[0][1]


class ConstraintCandidateEngine:
    def __init__(self, *, axis_tolerance: float = 1e-9, metric_tolerance: float = 1e-6) -> None:
        if axis_tolerance < 0 or metric_tolerance < 0:
            raise ValueError("constraint tolerances must be non-negative")
        self.axis_tolerance = axis_tolerance
        self.metric_tolerance = metric_tolerance

    def build(self, entities: tuple[GeometryPrimitive, ...]) -> tuple[ConstraintCandidate, ...]:
        ordered = tuple(sorted(entities, key=lambda item: item.entity_id))
        result: list[ConstraintCandidate] = []

        lines = tuple(entity for entity in ordered if isinstance(entity, Line))
        circles = tuple(entity for entity in ordered if isinstance(entity, Circle))

        for entity in lines:
            dx = entity.end.x - entity.start.x
            dy = entity.end.y - entity.start.y
            if abs(dy) <= self.axis_tolerance and abs(dx) > self.axis_tolerance:
                result.append(self._single("HORIZONTAL", entity.entity_id))
            if abs(dx) <= self.axis_tolerance and abs(dy) > self.axis_tolerance:
                result.append(self._single("VERTICAL", entity.entity_id))

        for first, second in combinations(lines, 2):
            ax, ay = first.end.x - first.start.x, first.end.y - first.start.y
            bx, by = second.end.x - second.start.x, second.end.y - second.start.y
            norm_product = max(first.length * second.length, 1e-15)
            cross = ax * by - ay * bx
            dot = ax * bx + ay * by
            if abs(cross) / norm_product <= self.metric_tolerance:
                result.append(self._pair("PARALLEL", first.entity_id, second.entity_id))
            if abs(dot) / norm_product <= self.metric_tolerance:
                result.append(self._pair("PERPENDICULAR", first.entity_id, second.entity_id))
            if isclose(first.length, second.length, abs_tol=self.metric_tolerance, rel_tol=0.0):
                result.append(self._pair("EQUAL", first.entity_id, second.entity_id))

        for first, second in combinations(circles, 2):
            if self._points_close(first.center, second.center):
                result.append(self._pair("CONCENTRIC", first.entity_id, second.entity_id))
            if isclose(first.radius, second.radius, abs_tol=self.metric_tolerance, rel_tol=0.0):
                result.append(self._pair("EQUAL", first.entity_id, second.entity_id))

        # Topological contact is deliberately finite/observable: an explicit point or
        # a LINE/ARC endpoint must lie on the other primitive. Pure crossing of two
        # interiors is not promoted as COINCIDENT.
        for first, second in combinations(ordered, 2):
            if self._observable_contact(first, second):
                result.append(self._pair("COINCIDENT", first.entity_id, second.entity_id))
            if self._are_tangent(first, second):
                result.append(self._pair("TANGENT", first.entity_id, second.entity_id))

        # Symmetry is only inferred when an explicit LINE entity supplies the axis.
        peers = tuple(entity for entity in ordered if isinstance(entity, (PointEntity, Circle)))
        for axis in lines:
            for first, second in combinations(peers, 2):
                if self._symmetric_about_axis(first, second, axis):
                    result.append(self._symmetric(first.entity_id, second.entity_id, axis.entity_id))

        # Candidate IDs are deterministic, but keep a defensive de-duplication boundary
        # because one observable contact can satisfy multiple endpoint checks.
        by_id = {candidate.constraint_id: candidate for candidate in result}
        return tuple(by_id[key] for key in sorted(by_id))

    def _observable_contact(self, first: GeometryPrimitive, second: GeometryPrimitive) -> bool:
        return any(
            _distance_to_primitive(point, second) <= self.metric_tolerance
            for point in self._contact_points(first)
        ) or any(
            _distance_to_primitive(point, first) <= self.metric_tolerance
            for point in self._contact_points(second)
        )

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

    def _are_tangent(self, first: GeometryPrimitive, second: GeometryPrimitive) -> bool:
        if isinstance(first, Line) and isinstance(second, (Circle, Arc)):
            return self._line_round_tangent(first, second)
        if isinstance(second, Line) and isinstance(first, (Circle, Arc)):
            return self._line_round_tangent(second, first)
        if isinstance(first, (Circle, Arc)) and isinstance(second, (Circle, Arc)):
            return self._round_round_tangent(first, second)
        return False

    def _line_round_tangent(self, line: Line, round_entity: Circle | Arc) -> bool:
        if line.length <= self.metric_tolerance:
            return False
        nearest, parameter = self._nearest_point_on_line(round_entity.center, line)
        if parameter < -self.metric_tolerance or parameter > 1.0 + self.metric_tolerance:
            return False
        radial_distance = hypot(nearest.x - round_entity.center.x, nearest.y - round_entity.center.y)
        if not isclose(
            radial_distance, round_entity.radius, abs_tol=self.metric_tolerance, rel_tol=0.0
        ):
            return False
        return not isinstance(round_entity, Arc) or self._point_on_arc(nearest, round_entity)

    def _round_round_tangent(
        self, first: Circle | Arc, second: Circle | Arc
    ) -> bool:
        dx = second.center.x - first.center.x
        dy = second.center.y - first.center.y
        distance = hypot(dx, dy)
        if distance <= self.metric_tolerance:
            return False
        external = first.radius + second.radius
        internal = abs(first.radius - second.radius)
        if not (
            isclose(distance, external, abs_tol=self.metric_tolerance, rel_tol=0.0)
            or isclose(distance, internal, abs_tol=self.metric_tolerance, rel_tol=0.0)
        ):
            return False

        # At tangency the standard two-circle intersection solution has h == 0.
        axis_distance = (
            first.radius * first.radius
            - second.radius * second.radius
            + distance * distance
        ) / (2.0 * distance)
        tangent = Point2D(
            first.center.x + dx * axis_distance / distance,
            first.center.y + dy * axis_distance / distance,
        )
        if isinstance(first, Arc) and not self._point_on_arc(tangent, first):
            return False
        if isinstance(second, Arc) and not self._point_on_arc(tangent, second):
            return False
        return True

    @staticmethod
    def _nearest_point_on_line(point: Point2D, line: Line) -> tuple[Point2D, float]:
        dx = line.end.x - line.start.x
        dy = line.end.y - line.start.y
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return line.start, 0.0
        parameter = (
            (point.x - line.start.x) * dx + (point.y - line.start.y) * dy
        ) / length_sq
        return Point2D(line.start.x + parameter * dx, line.start.y + parameter * dy), parameter

    @staticmethod
    def _point_on_arc(point: Point2D, arc: Arc) -> bool:
        angle = degrees(atan2(point.y - arc.center.y, point.x - arc.center.x))
        return _angle_on_arc(angle, arc.start_angle_deg, arc.end_angle_deg)

    def _symmetric_about_axis(
        self, first: PointEntity | Circle, second: PointEntity | Circle, axis: Line
    ) -> bool:
        if type(first) is not type(second):
            return False
        if isinstance(first, Circle) and isinstance(second, Circle):
            if not isclose(
                first.radius, second.radius, abs_tol=self.metric_tolerance, rel_tol=0.0
            ):
                return False
            first_point, second_point = first.center, second.center
        elif isinstance(first, PointEntity) and isinstance(second, PointEntity):
            first_point, second_point = first.point, second.point
        else:
            return False
        reflected = self._reflect_about_line(first_point, axis)
        return self._points_close(reflected, second_point)

    def _reflect_about_line(self, point: Point2D, axis: Line) -> Point2D:
        dx = axis.end.x - axis.start.x
        dy = axis.end.y - axis.start.y
        length_sq = dx * dx + dy * dy
        if length_sq <= self.axis_tolerance * self.axis_tolerance:
            return Point2D(float("inf"), float("inf"))
        parameter = (
            (point.x - axis.start.x) * dx + (point.y - axis.start.y) * dy
        ) / length_sq
        foot_x = axis.start.x + parameter * dx
        foot_y = axis.start.y + parameter * dy
        return Point2D(2.0 * foot_x - point.x, 2.0 * foot_y - point.y)

    def _points_close(self, first: Point2D, second: Point2D) -> bool:
        return hypot(first.x - second.x, first.y - second.y) <= self.metric_tolerance

    @staticmethod
    def _single(kind: str, entity_id: str) -> ConstraintCandidate:
        return ConstraintCandidate(f"C_{kind}_{entity_id}", kind, (entity_id,))  # type: ignore[arg-type]

    @staticmethod
    def _pair(kind: str, first: str, second: str) -> ConstraintCandidate:
        entity_ids = tuple(sorted((first, second)))
        return ConstraintCandidate(
            f"C_{kind}_{entity_ids[0]}_{entity_ids[1]}",
            kind,  # type: ignore[arg-type]
            entity_ids,
        )

    @staticmethod
    def _symmetric(first: str, second: str, axis: str) -> ConstraintCandidate:
        peers = tuple(sorted((first, second)))
        entity_ids = (peers[0], peers[1], axis)
        return ConstraintCandidate(
            f"C_SYMMETRIC_{peers[0]}_{peers[1]}_ABOUT_{axis}",
            "SYMMETRIC",
            entity_ids,
        )


class DimensionBinder:
    def __init__(self, matcher: AnchorEntityMatcher | None = None) -> None:
        self.matcher = matcher or AnchorEntityMatcher()

    def bind(
        self,
        entities: tuple[GeometryPrimitive, ...],
        measurements: tuple[MeasurementRef, ...],
    ) -> tuple[tuple[DimensionBinding, ...], tuple[UnresolvedBinding, ...]]:
        by_id = {entity.entity_id: entity for entity in entities}
        dimensions: list[DimensionBinding] = []
        unresolved: list[UnresolvedBinding] = []

        for measurement in sorted(measurements, key=lambda item: item.measurement_id):
            matches = [self.matcher.match_anchor(anchor, entities) for anchor in measurement.anchors]
            if any(match is None for match in matches):
                unresolved.append(
                    UnresolvedBinding(
                        measurement_id=measurement.measurement_id,
                        code="ANCHOR_ENTITY_UNRESOLVED_OR_AMBIGUOUS",
                        anchor_ids=tuple(anchor.anchor_id for anchor in measurement.anchors),
                    )
                )
                continue

            target_ids = tuple(sorted(set(match for match in matches if match is not None)))
            estimate = self._estimate(measurement.measurement_type, target_ids, by_id)
            dimensions.append(
                DimensionBinding(
                    dimension_id=f"D_{measurement.measurement_id}",
                    measurement_id=measurement.measurement_id,
                    measurement_type=measurement.measurement_type,
                    value=measurement.value,
                    unit=measurement.unit,
                    verified=measurement.verified,
                    source=measurement.source,
                    target_entity_ids=target_ids,
                    geometry_estimate=estimate,
                    uncertainty=measurement.uncertainty,
                )
            )

        return tuple(dimensions), tuple(unresolved)

    @staticmethod
    def _estimate(
        measurement_type: str,
        target_ids: tuple[str, ...],
        entities: dict[str, GeometryPrimitive],
    ) -> float | None:
        targets = tuple(entities[target_id] for target_id in target_ids)
        if measurement_type in {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"} and len(targets) == 1:
            target = targets[0]
            if isinstance(target, Circle):
                return 2.0 * target.radius
        if measurement_type == "RADIUS" and len(targets) == 1:
            target = targets[0]
            if isinstance(target, (Circle, Arc)):
                return target.radius
        if measurement_type == "CENTER_DISTANCE" and len(targets) == 2:
            if all(isinstance(target, Circle) for target in targets):
                first, second = targets
                return hypot(first.center.x - second.center.x, first.center.y - second.center.y)
        if measurement_type in {"LINEAR_EXTERNAL", "LINEAR_INTERNAL", "THICKNESS", "SLOT_WIDTH"} and len(targets) == 2:
            first, second = targets
            if isinstance(first, Line) and isinstance(second, Line):
                return _parallel_line_distance(first, second)
        return None


def _parallel_line_distance(first: Line, second: Line) -> float | None:
    ax = first.end.x - first.start.x
    ay = first.end.y - first.start.y
    bx = second.end.x - second.start.x
    by = second.end.y - second.start.y
    norm = first.length * second.length
    if norm == 0 or abs(ax * by - ay * bx) / norm > 1e-6:
        return None
    numerator = abs(
        ay * second.start.x
        - ax * second.start.y
        + first.end.x * first.start.y
        - first.end.y * first.start.x
    )
    denominator = hypot(ax, ay)
    return numerator / denominator if denominator else None


class GeometryConflictDetector:
    def __init__(self, *, tolerance: float = 0.05) -> None:
        if tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        self.tolerance = tolerance

    def detect(self, dimensions: tuple[DimensionBinding, ...]) -> tuple[GeometryConflict, ...]:
        result: list[GeometryConflict] = []
        for dimension in dimensions:
            if not dimension.verified or dimension.geometry_estimate is None:
                continue
            delta = abs(dimension.value - dimension.geometry_estimate)
            if delta > self.tolerance:
                result.append(
                    GeometryConflict(
                        conflict_id=f"GC_{dimension.measurement_id}",
                        code="VERIFIED_MEASUREMENT_VS_DERIVED_GEOMETRY",
                        measurement_id=dimension.measurement_id,
                        measured_value=dimension.value,
                        derived_value=dimension.geometry_estimate,
                        delta=delta,
                        tolerance=self.tolerance,
                    )
                )
        return tuple(result)


class GeometryPipeline:
    def __init__(
        self,
        *,
        constraint_engine: ConstraintCandidateEngine | None = None,
        binder: DimensionBinder | None = None,
        conflict_detector: GeometryConflictDetector | None = None,
    ) -> None:
        self.constraint_engine = constraint_engine or ConstraintCandidateEngine()
        self.binder = binder or DimensionBinder()
        self.conflict_detector = conflict_detector or GeometryConflictDetector()

    def build(
        self,
        primitives: tuple[GeometryPrimitive, ...],
        measurements: tuple[MeasurementRef, ...],
    ) -> GeometryDraft:
        entities = tuple(sorted(primitives, key=lambda item: item.entity_id))
        graph = GeometryGraph.build(entities)
        constraints = self.constraint_engine.build(entities)
        dimensions, unresolved = self.binder.bind(entities, measurements)
        conflicts = self.conflict_detector.detect(dimensions)
        return GeometryDraft(
            graph=graph,
            entities=entities,
            constraints=constraints,
            dimensions=dimensions,
            unresolved=unresolved,
            conflicts=conflicts,
        )
