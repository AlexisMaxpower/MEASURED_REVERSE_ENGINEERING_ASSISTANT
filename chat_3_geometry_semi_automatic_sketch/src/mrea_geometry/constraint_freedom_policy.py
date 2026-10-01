from __future__ import annotations

from math import hypot

from .constraint_freedom import (
    ConstraintFreedomAnalyzer as _BaseConstraintFreedomAnalyzer,
    _Equation,
    _ParameterLayout,
)
from .models import Arc, GeometryPrimitive, Line


class ConstraintFreedomAnalyzer(_BaseConstraintFreedomAnalyzer):
    """Public DOF analyzer with explicit topology-witness rules.

    The numerical core lives in ``constraint_freedom``. This policy layer tightens
    COINCIDENT handling so common line-endpoint topology contributes the correct two local
    equations, while arc-contact cases that need an explicit endpoint/curve witness remain
    fail-closed instead of silently projecting onto the parent circle.
    """

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
            if len(pairs) > 1 and (
                abs(pairs[1][0] - pairs[0][0]) <= self.ambiguity_tolerance_mm
            ):
                return None
            _, first_ordinal, second_ordinal = pairs[0]
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
