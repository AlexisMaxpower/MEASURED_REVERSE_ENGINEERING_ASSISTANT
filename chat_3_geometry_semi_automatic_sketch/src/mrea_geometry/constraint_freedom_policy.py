from __future__ import annotations

from math import acos, cos, degrees, hypot, isfinite, radians

from .constraint_freedom import (
    ConstraintFreedomAnalyzer as _BaseConstraintFreedomAnalyzer,
    _Equation,
    _ParameterLayout,
)
from .models import Arc, DimensionBinding, GeometryPrimitive, Line


class ConstraintFreedomAnalyzer(_BaseConstraintFreedomAnalyzer):
    """Public DOF analyzer with explicit topology-witness rules.

    The numerical core lives in ``constraint_freedom``. This policy layer tightens
    topology-sensitive relations so exact local DOF is published only when the current
    geometry exposes an unambiguous witness. Unsupported or ambiguous topology remains
    fail-closed instead of being projected onto guessed endpoints/rays.
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

        if isinstance(first, Arc) or isinstance(second, Arc):
            return None

        return super()._coincident_equations(first_id, second_id, entities, layout)

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
        pairs: list[tuple[float, int, int]] = []
        for first_ordinal in (0, 1):
            first_point = layout.endpoint(layout.values, first_id, first_ordinal)
            for second_ordinal in (0, 1):
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
