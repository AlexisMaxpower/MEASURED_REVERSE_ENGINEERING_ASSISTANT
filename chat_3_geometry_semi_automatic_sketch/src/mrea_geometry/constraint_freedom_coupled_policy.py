from __future__ import annotations

from contextvars import ContextVar
from math import hypot

from .constraint_freedom import (
    ConstraintFreedomDiagnosis,
    _Equation,
    _ParameterLayout,
)
from .constraint_freedom_policy import (
    ConstraintFreedomAnalyzer as _TopologyConstraintFreedomAnalyzer,
)
from .constraint_system import ConstraintSystemDiagnosis
from .constraints import ConstraintResolution, ResolvedConstraint
from .models import Arc, GeometryDraft, GeometryPrimitive, Line


class ConstraintFreedomAnalyzer(_TopologyConstraintFreedomAnalyzer):
    """Topology-safe DOF policy with explicit cross-relation endpoint witnesses.

    Pass 18 deliberately rejected tangency at a trimmed Arc boundary because an entity-only
    ``TANGENT`` relation cannot identify whether that boundary contact is intentional. This
    layer admits the narrow coupled case where the same resolved entity pair also carries a
    supported ``COINCIDENT`` relation and the current geometry exposes one unique shared
    endpoint that is exactly the tangent contact. The extra relation is evidence only; no
    endpoint ordinal, branch, tolerance, confidence, or geometry is invented.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._resolution_context: ContextVar[tuple[ResolvedConstraint, ...]] = ContextVar(
            f"mrea_constraint_freedom_resolution_{id(self)}",
            default=(),
        )

    def analyze(
        self,
        draft: GeometryDraft,
        resolution: ConstraintResolution,
        *,
        system_diagnosis: ConstraintSystemDiagnosis | None = None,
    ) -> ConstraintFreedomDiagnosis:
        token = self._resolution_context.set(tuple(resolution.constraints))
        try:
            return super().analyze(
                draft,
                resolution,
                system_diagnosis=system_diagnosis,
            )
        finally:
            # The analyzer can be reused safely. Coupled evidence from one diagnosis must
            # never leak into a later diagnosis that does not contain the same relation.
            self._resolution_context.reset(token)

    def _arc_tangent_equations(
        self,
        first_id: str,
        second_id: str,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        interior = super()._arc_tangent_equations(
            first_id,
            second_id,
            entities,
            layout,
        )
        if interior is not None:
            return interior

        if not self._has_resolved_pair_relation("COINCIDENT", first_id, second_id):
            return None

        witness = self._unique_endpoint_pair(first_id, second_id, layout)
        if witness is None:
            # A COINCIDENT relation without one unique endpoint-to-endpoint witness does
            # not identify the active tangency topology and therefore cannot unlock it.
            return None

        first = entities[first_id]
        second = entities[second_id]

        if isinstance(first, Line) and isinstance(second, Arc):
            if not self._line_arc_endpoint_tangent_witness(
                first_id,
                second_id,
                witness,
                layout,
            ):
                return None
            return (
                self._line_arc_endpoint_tangent_equation(
                    first_id,
                    second_id,
                    witness,
                    layout,
                ),
            )

        if isinstance(second, Line) and isinstance(first, Arc):
            reversed_witness = (witness[1], witness[0])
            if not self._line_arc_endpoint_tangent_witness(
                second_id,
                first_id,
                reversed_witness,
                layout,
            ):
                return None
            return (
                self._line_arc_endpoint_tangent_equation(
                    second_id,
                    first_id,
                    reversed_witness,
                    layout,
                ),
            )

        if isinstance(first, Arc) and isinstance(second, Arc):
            if not self._arc_arc_endpoint_tangent_witness(
                first_id,
                second_id,
                witness,
                layout,
            ):
                return None
            return (
                self._arc_arc_endpoint_tangent_equation(
                    first_id,
                    second_id,
                    witness,
                    layout,
                ),
            )

        # Arc-Circle boundary tangency remains unsupported because Circle exposes no
        # endpoint ordinal that a separate COINCIDENT relation could prove.
        return None

    def _has_resolved_pair_relation(
        self,
        kind: str,
        first_id: str,
        second_id: str,
    ) -> bool:
        target = tuple(sorted((first_id, second_id)))
        for constraint in self._resolution_context.get():
            if constraint.kind != kind or len(constraint.entity_ids) != 2:
                continue
            if tuple(sorted(constraint.entity_ids)) == target:
                return True
        return False

    def _line_arc_endpoint_tangent_witness(
        self,
        line_id: str,
        arc_id: str,
        witness: tuple[int, int],
        layout: _ParameterLayout,
    ) -> bool:
        line_ordinal, arc_ordinal = witness
        contact = self._line_round_tangent_contact_including_endpoints(
            layout.values,
            line_id,
            arc_id,
            layout,
        )
        if contact is None:
            return False

        line_endpoint = layout.endpoint(layout.values, line_id, line_ordinal)
        arc_endpoint = layout.endpoint(layout.values, arc_id, arc_ordinal)
        return self._points_match(contact, line_endpoint) and self._points_match(
            contact,
            arc_endpoint,
        )

    def _arc_arc_endpoint_tangent_witness(
        self,
        first_id: str,
        second_id: str,
        witness: tuple[int, int],
        layout: _ParameterLayout,
    ) -> bool:
        contact = self._round_round_tangent_contact(
            layout.values,
            first_id,
            second_id,
            layout,
        )
        if contact is None:
            return False

        first_endpoint = layout.endpoint(layout.values, first_id, witness[0])
        second_endpoint = layout.endpoint(layout.values, second_id, witness[1])
        return self._points_match(contact, first_endpoint) and self._points_match(
            contact,
            second_endpoint,
        )

    def _line_arc_endpoint_tangent_equation(
        self,
        line_id: str,
        arc_id: str,
        witness: tuple[int, int],
        layout: _ParameterLayout,
    ) -> _Equation:
        line_ordinal, arc_ordinal = witness

        def equation(vector: tuple[float, ...]) -> float:
            line_contact = layout.endpoint(vector, line_id, line_ordinal)
            line_outer = layout.endpoint(vector, line_id, 1 - line_ordinal)
            arc_contact = layout.endpoint(vector, arc_id, arc_ordinal)
            cx, cy, _, _, _ = layout.arc(vector, arc_id)
            line_dx = line_outer[0] - line_contact[0]
            line_dy = line_outer[1] - line_contact[1]
            radius_dx = arc_contact[0] - cx
            radius_dy = arc_contact[1] - cy
            return line_dx * radius_dx + line_dy * radius_dy

        return equation

    def _arc_arc_endpoint_tangent_equation(
        self,
        first_id: str,
        second_id: str,
        witness: tuple[int, int],
        layout: _ParameterLayout,
    ) -> _Equation:
        first_ordinal, second_ordinal = witness

        def equation(vector: tuple[float, ...]) -> float:
            first_contact = layout.endpoint(vector, first_id, first_ordinal)
            second_contact = layout.endpoint(vector, second_id, second_ordinal)
            first_cx, first_cy, _, _, _ = layout.arc(vector, first_id)
            second_cx, second_cy, _, _, _ = layout.arc(vector, second_id)
            first_rx = first_contact[0] - first_cx
            first_ry = first_contact[1] - first_cy
            second_rx = second_contact[0] - second_cx
            second_ry = second_contact[1] - second_cy
            return first_rx * second_ry - first_ry * second_rx

        return equation

    def _line_round_tangent_contact_including_endpoints(
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
        if length_sq <= self.degenerate_epsilon or radius <= self.degenerate_epsilon:
            return None

        length = length_sq**0.5
        distance = abs(dx * (cy - sy) - dy * (cx - sx)) / length
        if abs(distance - radius) > self.ambiguity_tolerance_mm:
            return None

        parameter = ((cx - sx) * dx + (cy - sy) * dy) / length_sq
        endpoint_margin = self.ambiguity_tolerance_mm / length
        if parameter < -endpoint_margin or parameter > 1.0 + endpoint_margin:
            return None
        return sx + parameter * dx, sy + parameter * dy

    def _points_match(
        self,
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> bool:
        return hypot(first[0] - second[0], first[1] - second[1]) <= self.ambiguity_tolerance_mm
