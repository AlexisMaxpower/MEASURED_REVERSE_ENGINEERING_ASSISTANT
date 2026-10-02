from __future__ import annotations

from math import acos, atan2, cos, degrees, hypot, isfinite, radians

from .constraint_freedom import (
    ConstraintFreedomAnalyzer as _BaseConstraintFreedomAnalyzer,
    _Equation,
    _ParameterLayout,
)
from .constraints import ResolvedConstraint
from .models import Arc, Circle, DimensionBinding, GeometryPrimitive, Line


class ConstraintFreedomAnalyzer(_BaseConstraintFreedomAnalyzer):
    """Public DOF analyzer with explicit topology-witness rules.

    The numerical core lives in ``constraint_freedom``. This policy layer tightens
    topology-sensitive relations so exact local DOF is published only when the current
    geometry exposes an unambiguous witness. Unsupported or ambiguous topology remains
    fail-closed instead of being projected onto guessed endpoints/rays/contact points.
    """

    def __init__(
        self,
        *,
        angular_witness_tolerance_deg: float = 1e-6,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if (
            not isfinite(angular_witness_tolerance_deg)
            or angular_witness_tolerance_deg < 0.0
        ):
            raise ValueError(
                "angular_witness_tolerance_deg must be finite and non-negative"
            )
        self.angular_witness_tolerance_deg = float(angular_witness_tolerance_deg)

    def _constraint_equations(
        self,
        constraint: ResolvedConstraint,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        if constraint.kind == "TANGENT" and len(constraint.entity_ids) == 2:
            first_id, second_id = constraint.entity_ids
            first = entities.get(first_id)
            second = entities.get(second_id)
            if isinstance(first, Arc) or isinstance(second, Arc):
                return self._arc_tangent_equations(
                    first_id,
                    second_id,
                    entities,
                    layout,
                )
        return super()._constraint_equations(constraint, entities, layout)

    def _coincident_equations(
        self,
        first_id: str,
        second_id: str,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        first = entities[first_id]
        second = entities[second_id]

        if isinstance(first, Line) and isinstance(second, Line):
            witness = self._unique_line_endpoint_pair(first_id, second_id, layout)
            if witness is None:
                # Entity-only COINCIDENT does not identify endpoint ordinals. Proximity is
                # not itself a topology witness: if no unique endpoint pair is already
                # coincident within the declared tolerance, exact local DOF fails closed.
                return None
            return self._endpoint_pair_equations(first_id, second_id, witness, layout)

        if isinstance(first, Arc) or isinstance(second, Arc):
            witness = self._unique_endpoint_pair(first_id, second_id, layout)
            if witness is None:
                # Arc COINCIDENT is supported only when the current geometry exposes one
                # unique endpoint-to-endpoint witness. An entity-only relation does not say
                # which trimmed endpoint, or whether an endpoint-to-interior contact, was
                # intended. Those cases therefore stay fail-closed rather than guessing.
                return None
            return self._endpoint_pair_equations(first_id, second_id, witness, layout)

        return super()._coincident_equations(first_id, second_id, entities, layout)

    def _arc_tangent_equations(
        self,
        first_id: str,
        second_id: str,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        first = entities[first_id]
        second = entities[second_id]

        if isinstance(first, Line) and isinstance(second, Arc):
            contact = self._line_round_tangent_contact(
                layout.values,
                first_id,
                second_id,
                layout,
            )
            if contact is None or not self._point_is_strictly_inside_arc_span(
                contact,
                second_id,
                layout.values,
                layout,
            ):
                return None
            return (self._line_round_tangent_equation(first_id, second_id, layout),)

        if isinstance(second, Line) and isinstance(first, Arc):
            contact = self._line_round_tangent_contact(
                layout.values,
                second_id,
                first_id,
                layout,
            )
            if contact is None or not self._point_is_strictly_inside_arc_span(
                contact,
                first_id,
                layout.values,
                layout,
            ):
                return None
            return (self._line_round_tangent_equation(second_id, first_id, layout),)

        if isinstance(first, (Circle, Arc)) and isinstance(second, (Circle, Arc)):
            contact = self._round_round_tangent_contact(
                layout.values,
                first_id,
                second_id,
                layout,
            )
            if contact is None:
                return None
            if isinstance(first, Arc) and not self._point_is_strictly_inside_arc_span(
                contact,
                first_id,
                layout.values,
                layout,
            ):
                return None
            if isinstance(second, Arc) and not self._point_is_strictly_inside_arc_span(
                contact,
                second_id,
                layout.values,
                layout,
            ):
                return None
            return (self._round_round_tangent_equation(first_id, second_id, layout),)

        return None

    def _dimension_equations(
        self,
        dimension: DimensionBinding,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        if dimension.measurement_type != "ANGLE":
            return super()._dimension_equations(dimension, entities, layout)

        ids = dimension.target_entity_ids
        if dimension.unit != "deg" or len(ids) != 2:
            return None
        if not all(isinstance(entities.get(entity_id), Line) for entity_id in ids):
            return None

        target = float(dimension.value)
        if not isfinite(target) or target < 0.0 or target > 180.0:
            return None

        uncertainty = dimension.uncertainty
        if uncertainty is not None:
            if not isfinite(uncertainty) or uncertainty < 0.0:
                return None
            angular_allowance = self.angular_witness_tolerance_deg + float(uncertainty)
        else:
            angular_allowance = self.angular_witness_tolerance_deg

        first_id, second_id = ids
        witness = self._unique_line_endpoint_pair(first_id, second_id, layout)
        if witness is None:
            # Without a unique shared endpoint, the entity pair does not identify which
            # rays define an included physical angle. Endpoint storage order must never be
            # used as a substitute for measurement topology.
            return None
        first_vertex_ordinal, second_vertex_ordinal = witness

        current_angle = self._line_ray_angle_deg(
            layout.values,
            first_id,
            second_id,
            first_vertex_ordinal,
            second_vertex_ordinal,
            layout,
        )
        if current_angle is None or abs(current_angle - target) > angular_allowance:
            # Exact local rank is evaluated only around geometry that is compatible with
            # the verified angular measurement (within explicit measurement uncertainty
            # plus a numerical witness epsilon). A mismatching image-derived shape cannot
            # be treated as if it already embodied verified physical truth.
            return None

        if (
            target <= self.angular_witness_tolerance_deg
            or abs(target - 180.0) <= self.angular_witness_tolerance_deg
        ):
            # dot-cos formulations have a zero first derivative at 0/180 degrees. The
            # signed cross product supplies the correct local one-equation rank, while the
            # current-angle witness above keeps the local branch (0 versus 180) explicit.
            return (
                lambda vector, first_id=first_id, second_id=second_id,
                first_vertex_ordinal=first_vertex_ordinal,
                second_vertex_ordinal=second_vertex_ordinal: self._line_ray_cross(
                    vector,
                    first_id,
                    second_id,
                    first_vertex_ordinal,
                    second_vertex_ordinal,
                    layout,
                ),
            )

        target_cosine = cos(radians(target))
        return (
            lambda vector, first_id=first_id, second_id=second_id,
            first_vertex_ordinal=first_vertex_ordinal,
            second_vertex_ordinal=second_vertex_ordinal,
            target_cosine=target_cosine: (
                self._line_ray_dot(
                    vector,
                    first_id,
                    second_id,
                    first_vertex_ordinal,
                    second_vertex_ordinal,
                    layout,
                )
                - target_cosine
                * self._line_ray_norm_product(
                    vector,
                    first_id,
                    second_id,
                    first_vertex_ordinal,
                    second_vertex_ordinal,
                    layout,
                )
            ),
        )

    def _unique_line_endpoint_pair(
        self,
        first_id: str,
        second_id: str,
        layout: _ParameterLayout,
    ) -> tuple[int, int] | None:
        return self._unique_endpoint_pair(first_id, second_id, layout)

    def _unique_endpoint_pair(
        self,
        first_id: str,
        second_id: str,
        layout: _ParameterLayout,
    ) -> tuple[int, int] | None:
        first_ordinals = layout.contact_ordinals(first_id)
        second_ordinals = layout.contact_ordinals(second_id)
        if not first_ordinals or not second_ordinals:
            return None

        pairs: list[tuple[float, int, int]] = []
        for first_ordinal in first_ordinals:
            first_point = layout.endpoint(layout.values, first_id, first_ordinal)
            for second_ordinal in second_ordinals:
                second_point = layout.endpoint(layout.values, second_id, second_ordinal)
                distance = hypot(
                    first_point[0] - second_point[0],
                    first_point[1] - second_point[1],
                )
                pairs.append((distance, first_ordinal, second_ordinal))

        pairs.sort(key=lambda item: (item[0], item[1], item[2]))
        nearest_distance, first_ordinal, second_ordinal = pairs[0]
        if nearest_distance > self.ambiguity_tolerance_mm:
            return None
        if len(pairs) > 1 and (
            abs(pairs[1][0] - nearest_distance) <= self.ambiguity_tolerance_mm
        ):
            return None
        return first_ordinal, second_ordinal

    @staticmethod
    def _endpoint_pair_equations(
        first_id: str,
        second_id: str,
        witness: tuple[int, int],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...]:
        first_ordinal, second_ordinal = witness
        return (
            lambda vector, first_id=first_id, second_id=second_id,
            first_ordinal=first_ordinal, second_ordinal=second_ordinal: (
                layout.endpoint(vector, first_id, first_ordinal)[0]
                - layout.endpoint(vector, second_id, second_ordinal)[0]
            ),
            lambda vector, first_id=first_id, second_id=second_id,
            first_ordinal=first_ordinal, second_ordinal=second_ordinal: (
                layout.endpoint(vector, first_id, first_ordinal)[1]
                - layout.endpoint(vector, second_id, second_ordinal)[1]
            ),
        )

    def _line_round_tangent_contact(
        self,
        vector: tuple[float, ...],
        line_id: str,
        round_id: str,
        layout: _ParameterLayout,
    ) -> tuple[float, float] | None:
        sx, sy, ex, ey = layout.line(vector, line_id)
        cx, cy, radius = layout.round(vector, round_id)
        dx, dy = ex - sx, ey - sy
        length_sq = dx * dx + dy * dy
        if length_sq <= self.degenerate_epsilon:
            return None
        length = length_sq**0.5
        distance = abs(dx * (cy - sy) - dy * (cx - sx)) / length
        if abs(distance - radius) > self.ambiguity_tolerance_mm:
            return None

        parameter = ((cx - sx) * dx + (cy - sy) * dy) / length_sq
        endpoint_margin = self.ambiguity_tolerance_mm / length
        if parameter <= endpoint_margin or parameter >= 1.0 - endpoint_margin:
            # Contact at/near a trimmed Line endpoint is an active-set boundary, not a
            # stable interior topology witness for an entity-only TANGENT relation.
            return None
        return sx + parameter * dx, sy + parameter * dy

    def _round_round_tangent_contact(
        self,
        vector: tuple[float, ...],
        first_id: str,
        second_id: str,
        layout: _ParameterLayout,
    ) -> tuple[float, float] | None:
        ax, ay, ar = layout.round(vector, first_id)
        bx, by, br = layout.round(vector, second_id)
        dx, dy = bx - ax, by - ay
        center_distance = hypot(dx, dy)
        if center_distance <= self.degenerate_epsilon:
            return None

        external_error = abs(center_distance - (ar + br))
        internal_error = abs(center_distance - abs(ar - br))
        candidates: list[str] = []
        if external_error <= self.ambiguity_tolerance_mm:
            candidates.append("EXTERNAL")
        if internal_error <= self.ambiguity_tolerance_mm:
            candidates.append("INTERNAL")
        if len(candidates) != 1:
            # No compatible branch, or more than one branch inside the numerical witness
            # tolerance, means the contact topology is not uniquely established.
            return None

        ux, uy = dx / center_distance, dy / center_distance
        if candidates[0] == "EXTERNAL":
            return ax + ux * ar, ay + uy * ar

        if abs(ar - br) <= self.degenerate_epsilon:
            return None
        if ar > br:
            return ax + ux * ar, ay + uy * ar
        return bx - ux * br, by - uy * br

    def _point_is_strictly_inside_arc_span(
        self,
        point: tuple[float, float],
        arc_id: str,
        vector: tuple[float, ...],
        layout: _ParameterLayout,
    ) -> bool:
        cx, cy, radius, start_deg, end_deg = layout.arc(vector, arc_id)
        if radius <= self.degenerate_epsilon:
            return False
        span = (end_deg - start_deg) % 360.0
        if span <= 2.0 * self.angular_witness_tolerance_deg:
            return False

        point_angle = degrees(atan2(point[1] - cy, point[0] - cx)) % 360.0
        start = start_deg % 360.0
        offset = (point_angle - start) % 360.0
        if offset <= self.angular_witness_tolerance_deg:
            return False
        if span - offset <= self.angular_witness_tolerance_deg:
            return False
        return offset < span

    @staticmethod
    def _line_ray(
        vector: tuple[float, ...],
        entity_id: str,
        vertex_ordinal: int,
        layout: _ParameterLayout,
    ) -> tuple[float, float]:
        vertex = layout.endpoint(vector, entity_id, vertex_ordinal)
        outer = layout.endpoint(vector, entity_id, 1 - vertex_ordinal)
        return outer[0] - vertex[0], outer[1] - vertex[1]

    def _line_ray_angle_deg(
        self,
        vector: tuple[float, ...],
        first_id: str,
        second_id: str,
        first_vertex_ordinal: int,
        second_vertex_ordinal: int,
        layout: _ParameterLayout,
    ) -> float | None:
        first = self._line_ray(vector, first_id, first_vertex_ordinal, layout)
        second = self._line_ray(vector, second_id, second_vertex_ordinal, layout)
        norm_product = hypot(*first) * hypot(*second)
        if norm_product <= self.degenerate_epsilon:
            return None
        cosine = (first[0] * second[0] + first[1] * second[1]) / norm_product
        cosine = max(-1.0, min(1.0, cosine))
        return degrees(acos(cosine))

    def _line_ray_dot(
        self,
        vector: tuple[float, ...],
        first_id: str,
        second_id: str,
        first_vertex_ordinal: int,
        second_vertex_ordinal: int,
        layout: _ParameterLayout,
    ) -> float:
        first = self._line_ray(vector, first_id, first_vertex_ordinal, layout)
        second = self._line_ray(vector, second_id, second_vertex_ordinal, layout)
        return first[0] * second[0] + first[1] * second[1]

    def _line_ray_cross(
        self,
        vector: tuple[float, ...],
        first_id: str,
        second_id: str,
        first_vertex_ordinal: int,
        second_vertex_ordinal: int,
        layout: _ParameterLayout,
    ) -> float:
        first = self._line_ray(vector, first_id, first_vertex_ordinal, layout)
        second = self._line_ray(vector, second_id, second_vertex_ordinal, layout)
        return first[0] * second[1] - first[1] * second[0]

    def _line_ray_norm_product(
        self,
        vector: tuple[float, ...],
        first_id: str,
        second_id: str,
        first_vertex_ordinal: int,
        second_vertex_ordinal: int,
        layout: _ParameterLayout,
    ) -> float:
        first = self._line_ray(vector, first_id, first_vertex_ordinal, layout)
        second = self._line_ray(vector, second_id, second_vertex_ordinal, layout)
        return hypot(*first) * hypot(*second)
