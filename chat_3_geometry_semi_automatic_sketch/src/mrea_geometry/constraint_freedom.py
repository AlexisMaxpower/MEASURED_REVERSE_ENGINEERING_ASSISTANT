from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, isfinite, pi, radians, sin
from typing import Callable, Literal

from .constraint_system import ConstraintSystemAnalyzer, ConstraintSystemDiagnosis
from .constraints import ConstraintResolution, ResolvedConstraint
from .models import (
    Arc,
    Circle,
    DimensionBinding,
    GeometryDraft,
    GeometryPrimitive,
    Line,
    PointEntity,
)

ConstraintFreedomStatus = Literal[
    "FULLY_CONSTRAINED",
    "CONSTRAINED_UP_TO_FRAME",
    "UNDER_CONSTRAINED",
    "INDETERMINATE",
    "CONFLICTING",
]

_Equation = Callable[[tuple[float, ...]], float]


@dataclass(frozen=True, slots=True)
class ConstraintFreedomIssue:
    issue_id: str
    code: str
    message: str
    constraint_ids: tuple[str, ...] = ()
    dimension_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        result = {
            "issue_id": self.issue_id,
            "code": self.code,
            "message": self.message,
        }
        if self.constraint_ids:
            result["constraint_ids"] = list(self.constraint_ids)
        if self.dimension_ids:
            result["dimension_ids"] = list(self.dimension_ids)
        if self.entity_ids:
            result["entity_ids"] = list(self.entity_ids)
        return result


@dataclass(frozen=True, slots=True)
class ConstraintFreedomDiagnosis:
    """Read-only local DOF diagnosis for the supported Chat-3 geometry vocabulary.

    ``degrees_of_freedom`` is the nullity of the local constraint Jacobian. Frame DOF are
    rigid-body motions that remain legal in the current coordinate frame; internal DOF are
    the remaining shape freedoms after those frame motions are removed.
    """

    status: ConstraintFreedomStatus
    variable_count: int
    supported_equation_count: int
    supported_rank: int
    degrees_of_freedom: int | None
    frame_degrees_of_freedom: int | None
    internal_degrees_of_freedom: int | None
    issues: tuple[ConstraintFreedomIssue, ...]
    unsupported_constraint_ids: tuple[str, ...] = ()
    unsupported_dimension_ids: tuple[str, ...] = ()

    @property
    def fully_constrained(self) -> bool:
        return self.status == "FULLY_CONSTRAINED"

    @property
    def constrained_up_to_frame(self) -> bool:
        return self.status in {"FULLY_CONSTRAINED", "CONSTRAINED_UP_TO_FRAME"}

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "variable_count": self.variable_count,
            "supported_equation_count": self.supported_equation_count,
            "supported_rank": self.supported_rank,
            "degrees_of_freedom": self.degrees_of_freedom,
            "frame_degrees_of_freedom": self.frame_degrees_of_freedom,
            "internal_degrees_of_freedom": self.internal_degrees_of_freedom,
            "fully_constrained": self.fully_constrained,
            "constrained_up_to_frame": self.constrained_up_to_frame,
            "issues": [item.to_dict() for item in self.issues],
            "unsupported_constraint_ids": list(self.unsupported_constraint_ids),
            "unsupported_dimension_ids": list(self.unsupported_dimension_ids),
        }


@dataclass(frozen=True, slots=True)
class _EntitySlot:
    kind: str
    offset: int
    size: int


class _ParameterLayout:
    def __init__(self, entities: tuple[GeometryPrimitive, ...]) -> None:
        values: list[float] = []
        slots: dict[str, _EntitySlot] = {}
        for entity in sorted(entities, key=lambda item: item.entity_id):
            offset = len(values)
            if isinstance(entity, PointEntity):
                values.extend((entity.point.x, entity.point.y))
                slots[entity.entity_id] = _EntitySlot("POINT", offset, 2)
            elif isinstance(entity, Line):
                values.extend((entity.start.x, entity.start.y, entity.end.x, entity.end.y))
                slots[entity.entity_id] = _EntitySlot("LINE", offset, 4)
            elif isinstance(entity, Circle):
                values.extend((entity.center.x, entity.center.y, entity.radius))
                slots[entity.entity_id] = _EntitySlot("CIRCLE", offset, 3)
            elif isinstance(entity, Arc):
                values.extend(
                    (
                        entity.center.x,
                        entity.center.y,
                        entity.radius,
                        entity.start_angle_deg,
                        entity.end_angle_deg,
                    )
                )
                slots[entity.entity_id] = _EntitySlot("ARC", offset, 5)
            else:  # pragma: no cover - GeometryPrimitive is a closed union.
                raise TypeError(f"unsupported geometry primitive: {type(entity)!r}")
        self.values = tuple(float(value) for value in values)
        self.slots = slots

    def point(self, vector: tuple[float, ...], entity_id: str) -> tuple[float, float]:
        slot = self.slots[entity_id]
        if slot.kind != "POINT":
            raise TypeError(f"{entity_id} is not a point")
        return vector[slot.offset], vector[slot.offset + 1]

    def line(
        self, vector: tuple[float, ...], entity_id: str
    ) -> tuple[float, float, float, float]:
        slot = self.slots[entity_id]
        if slot.kind != "LINE":
            raise TypeError(f"{entity_id} is not a line")
        offset = slot.offset
        return (
            vector[offset],
            vector[offset + 1],
            vector[offset + 2],
            vector[offset + 3],
        )

    def round(
        self, vector: tuple[float, ...], entity_id: str
    ) -> tuple[float, float, float]:
        slot = self.slots[entity_id]
        if slot.kind not in {"CIRCLE", "ARC"}:
            raise TypeError(f"{entity_id} is not round geometry")
        offset = slot.offset
        return vector[offset], vector[offset + 1], vector[offset + 2]

    def arc(
        self, vector: tuple[float, ...], entity_id: str
    ) -> tuple[float, float, float, float, float]:
        slot = self.slots[entity_id]
        if slot.kind != "ARC":
            raise TypeError(f"{entity_id} is not an arc")
        offset = slot.offset
        return (
            vector[offset],
            vector[offset + 1],
            vector[offset + 2],
            vector[offset + 3],
            vector[offset + 4],
        )

    def endpoint(
        self, vector: tuple[float, ...], entity_id: str, ordinal: int
    ) -> tuple[float, float]:
        slot = self.slots[entity_id]
        if slot.kind == "LINE":
            sx, sy, ex, ey = self.line(vector, entity_id)
            return (sx, sy) if ordinal == 0 else (ex, ey)
        if slot.kind == "ARC":
            cx, cy, radius, start_deg, end_deg = self.arc(vector, entity_id)
            angle = start_deg if ordinal == 0 else end_deg
            theta = radians(angle)
            return cx + radius * cos(theta), cy + radius * sin(theta)
        if slot.kind == "POINT" and ordinal == 0:
            return self.point(vector, entity_id)
        raise TypeError(f"{entity_id} does not expose endpoint {ordinal}")

    def contact_ordinals(self, entity_id: str) -> tuple[int, ...]:
        kind = self.slots[entity_id].kind
        if kind == "POINT":
            return (0,)
        if kind in {"LINE", "ARC"}:
            return (0, 1)
        return ()


class ConstraintFreedomAnalyzer:
    """Compute local sketch freedom without solving or moving geometry.

    Exact DOF is published only when every accepted relation and every verified bound
    dimension can be represented by this analyzer and the draft has no unresolved binding
    or physical-measurement conflict. Unsupported semantics fail closed as INDETERMINATE.
    """

    _LINEAR_DIMENSION_TYPES = {
        "LINEAR_EXTERNAL",
        "LINEAR_INTERNAL",
        "THICKNESS",
        "SLOT_WIDTH",
    }

    def __init__(
        self,
        *,
        finite_difference_step: float = 1e-6,
        rank_tolerance: float = 1e-8,
        ambiguity_tolerance_mm: float = 1e-9,
        degenerate_epsilon: float = 1e-12,
    ) -> None:
        if not isfinite(finite_difference_step) or finite_difference_step <= 0.0:
            raise ValueError("finite_difference_step must be finite and positive")
        if not isfinite(rank_tolerance) or rank_tolerance <= 0.0:
            raise ValueError("rank_tolerance must be finite and positive")
        if not isfinite(ambiguity_tolerance_mm) or ambiguity_tolerance_mm < 0.0:
            raise ValueError("ambiguity_tolerance_mm must be finite and non-negative")
        if not isfinite(degenerate_epsilon) or degenerate_epsilon <= 0.0:
            raise ValueError("degenerate_epsilon must be finite and positive")
        self.finite_difference_step = float(finite_difference_step)
        self.rank_tolerance = float(rank_tolerance)
        self.ambiguity_tolerance_mm = float(ambiguity_tolerance_mm)
        self.degenerate_epsilon = float(degenerate_epsilon)

    def analyze(
        self,
        draft: GeometryDraft,
        resolution: ConstraintResolution,
        *,
        system_diagnosis: ConstraintSystemDiagnosis | None = None,
    ) -> ConstraintFreedomDiagnosis:
        layout = _ParameterLayout(draft.entities)
        variable_count = len(layout.values)
        issues: list[ConstraintFreedomIssue] = []

        if variable_count == 0:
            issues.append(
                ConstraintFreedomIssue(
                    issue_id="CF-NO-GEOMETRY",
                    code="CONSTRAINT_FREEDOM_NO_GEOMETRY",
                    message="An empty geometry draft has no meaningful sketch-freedom diagnosis.",
                )
            )
            return self._indeterminate(variable_count, (), issues)

        global_diagnosis = system_diagnosis or ConstraintSystemAnalyzer().analyze(draft, resolution)
        if global_diagnosis.status == "CONFLICTING":
            issues.append(
                ConstraintFreedomIssue(
                    issue_id="CF-CONFLICTING-SYSTEM",
                    code="CONSTRAINT_FREEDOM_CONFLICTING_SYSTEM",
                    message=(
                        "Global constraint-system diagnosis is conflicting; no exact DOF claim "
                        "is published until those conflicts are resolved."
                    ),
                    constraint_ids=global_diagnosis.conflicting_constraint_ids,
                )
            )
            return self._conflicting(variable_count, issues)

        if draft.conflicts:
            measurement_ids = tuple(sorted(item.measurement_id for item in draft.conflicts))
            issues.append(
                ConstraintFreedomIssue(
                    issue_id="CF-PHYSICAL-CONFLICT",
                    code="CONSTRAINT_FREEDOM_PHYSICAL_MEASUREMENT_CONFLICT",
                    message=(
                        "Geometry conflicts with verified physical measurement truth; DOF "
                        "classification fails closed instead of treating image geometry as truth."
                    ),
                    dimension_ids=tuple(f"D_{item}" for item in measurement_ids),
                )
            )
            return self._conflicting(variable_count, issues)

        unresolved_measurement_ids = tuple(
            sorted({item.measurement_id for item in draft.unresolved})
        )
        if unresolved_measurement_ids:
            issues.append(
                ConstraintFreedomIssue(
                    issue_id="CF-UNRESOLVED-BINDING",
                    code="CONSTRAINT_FREEDOM_UNRESOLVED_MEASUREMENT_BINDING",
                    message=(
                        "At least one measurement binding remains unresolved; exact sketch "
                        "freedom cannot be claimed from an incomplete geometry/measurement map."
                    ),
                    dimension_ids=tuple(f"D_{item}" for item in unresolved_measurement_ids),
                )
            )

        entities = {item.entity_id: item for item in draft.entities}
        equations: list[_Equation] = []
        unsupported_constraints: list[str] = []
        unsupported_dimensions: list[str] = []

        for constraint in sorted(
            resolution.constraints,
            key=lambda item: (item.constraint_id, item.kind, item.entity_ids),
        ):
            built = self._constraint_equations(constraint, entities, layout)
            if built is None:
                unsupported_constraints.append(constraint.constraint_id)
                issues.append(
                    ConstraintFreedomIssue(
                        issue_id=f"CF-UNSUPPORTED-CONSTRAINT-{constraint.constraint_id}",
                        code="CONSTRAINT_FREEDOM_UNSUPPORTED_CONSTRAINT",
                        message=(
                            "Accepted constraint semantics are not represented safely by the "
                            "current local-DOF model; exact freedom fails closed."
                        ),
                        constraint_ids=(constraint.constraint_id,),
                        entity_ids=constraint.entity_ids,
                    )
                )
                continue
            equations.extend(built)

        for dimension in sorted(draft.dimensions, key=lambda item: item.dimension_id):
            if not dimension.verified:
                continue
            built = self._dimension_equations(dimension, entities, layout)
            if built is None:
                unsupported_dimensions.append(dimension.dimension_id)
                issues.append(
                    ConstraintFreedomIssue(
                        issue_id=f"CF-UNSUPPORTED-DIMENSION-{dimension.dimension_id}",
                        code="CONSTRAINT_FREEDOM_UNSUPPORTED_VERIFIED_DIMENSION",
                        message=(
                            "Verified dimension semantics are not represented safely by the "
                            "current local-DOF model; exact freedom fails closed."
                        ),
                        dimension_ids=(dimension.dimension_id,),
                        entity_ids=dimension.target_entity_ids,
                    )
                )
                continue
            equations.extend(built)

        try:
            jacobian = self._jacobian(equations, layout.values)
            normalized = self._normalize_rows(jacobian)
            rank = self._matrix_rank(normalized)
        except ValueError as exc:
            issues.append(
                ConstraintFreedomIssue(
                    issue_id="CF-NUMERICAL-FAIL-CLOSED",
                    code="CONSTRAINT_FREEDOM_NUMERICAL_FAILURE",
                    message=str(exc),
                )
            )
            return self._indeterminate(
                variable_count,
                equations,
                issues,
                unsupported_constraints=tuple(sorted(unsupported_constraints)),
                unsupported_dimensions=tuple(sorted(unsupported_dimensions)),
            )

        unsupported_constraint_ids = tuple(sorted(unsupported_constraints))
        unsupported_dimension_ids = tuple(sorted(unsupported_dimensions))
        if unresolved_measurement_ids or unsupported_constraint_ids or unsupported_dimension_ids:
            return ConstraintFreedomDiagnosis(
                status="INDETERMINATE",
                variable_count=variable_count,
                supported_equation_count=len(equations),
                supported_rank=rank,
                degrees_of_freedom=None,
                frame_degrees_of_freedom=None,
                internal_degrees_of_freedom=None,
                issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
                unsupported_constraint_ids=unsupported_constraint_ids,
                unsupported_dimension_ids=unsupported_dimension_ids,
            )

        dof = max(0, variable_count - rank)
        frame_dof = self._frame_freedom_rank(layout, normalized)
        internal_dof = max(0, dof - frame_dof)
        if dof == 0:
            status: ConstraintFreedomStatus = "FULLY_CONSTRAINED"
        elif internal_dof == 0:
            status = "CONSTRAINED_UP_TO_FRAME"
        else:
            status = "UNDER_CONSTRAINED"

        return ConstraintFreedomDiagnosis(
            status=status,
            variable_count=variable_count,
            supported_equation_count=len(equations),
            supported_rank=rank,
            degrees_of_freedom=dof,
            frame_degrees_of_freedom=frame_dof,
            internal_degrees_of_freedom=internal_dof,
            issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
        )

    def _constraint_equations(
        self,
        constraint: ResolvedConstraint,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        ids = constraint.entity_ids
        kind = constraint.kind
        if kind in {"HORIZONTAL", "VERTICAL"} and len(ids) == 1:
            if not isinstance(entities.get(ids[0]), Line):
                return None
            entity_id = ids[0]
            if kind == "HORIZONTAL":
                return (
                    lambda vector, entity_id=entity_id: (
                        layout.line(vector, entity_id)[3] - layout.line(vector, entity_id)[1]
                    ),
                )
            return (
                lambda vector, entity_id=entity_id: (
                    layout.line(vector, entity_id)[2] - layout.line(vector, entity_id)[0]
                ),
            )

        if kind in {"PARALLEL", "PERPENDICULAR"} and len(ids) == 2:
            if not all(isinstance(entities.get(entity_id), Line) for entity_id in ids):
                return None
            first, second = ids
            if kind == "PARALLEL":
                return (
                    lambda vector, first=first, second=second: self._line_cross(
                        layout.line(vector, first), layout.line(vector, second)
                    ),
                )
            return (
                lambda vector, first=first, second=second: self._line_dot(
                    layout.line(vector, first), layout.line(vector, second)
                ),
            )

        if kind == "EQUAL" and len(ids) == 2:
            first_entity = entities.get(ids[0])
            second_entity = entities.get(ids[1])
            first, second = ids
            if isinstance(first_entity, Line) and isinstance(second_entity, Line):
                return (
                    lambda vector, first=first, second=second: (
                        self._line_length_sq(layout.line(vector, first))
                        - self._line_length_sq(layout.line(vector, second))
                    ),
                )
            if isinstance(first_entity, (Circle, Arc)) and isinstance(
                second_entity, (Circle, Arc)
            ):
                return (
                    lambda vector, first=first, second=second: (
                        layout.round(vector, first)[2] - layout.round(vector, second)[2]
                    ),
                )
            return None

        if kind == "CONCENTRIC" and len(ids) == 2:
            if not all(isinstance(entities.get(entity_id), (Circle, Arc)) for entity_id in ids):
                return None
            first, second = ids
            return (
                lambda vector, first=first, second=second: (
                    layout.round(vector, first)[0] - layout.round(vector, second)[0]
                ),
                lambda vector, first=first, second=second: (
                    layout.round(vector, first)[1] - layout.round(vector, second)[1]
                ),
            )

        if kind == "COINCIDENT" and len(ids) == 2:
            return self._coincident_equations(ids[0], ids[1], entities, layout)

        if kind == "TANGENT" and len(ids) == 2:
            first_entity = entities.get(ids[0])
            second_entity = entities.get(ids[1])
            if isinstance(first_entity, Line) and isinstance(second_entity, (Circle, Arc)):
                return (self._line_round_tangent_equation(ids[0], ids[1], layout),)
            if isinstance(second_entity, Line) and isinstance(first_entity, (Circle, Arc)):
                return (self._line_round_tangent_equation(ids[1], ids[0], layout),)
            if isinstance(first_entity, (Circle, Arc)) and isinstance(
                second_entity, (Circle, Arc)
            ):
                return (self._round_round_tangent_equation(ids[0], ids[1], layout),)
            return None

        if kind == "SYMMETRIC" and len(ids) == 3:
            first_entity = entities.get(ids[0])
            second_entity = entities.get(ids[1])
            axis_entity = entities.get(ids[2])
            if not isinstance(axis_entity, Line):
                return None
            first, second, axis = ids
            if isinstance(first_entity, PointEntity) and isinstance(second_entity, PointEntity):
                return self._symmetry_equations(first, second, axis, layout, with_radius=False)
            if isinstance(first_entity, Circle) and isinstance(second_entity, Circle):
                return self._symmetry_equations(first, second, axis, layout, with_radius=True)
            return None

        return None

    def _dimension_equations(
        self,
        dimension: DimensionBinding,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        ids = dimension.target_entity_ids
        measurement_type = dimension.measurement_type

        if measurement_type in self._LINEAR_DIMENSION_TYPES and len(ids) == 2:
            if dimension.unit != "mm" or not all(
                isinstance(entities.get(entity_id), Line) for entity_id in ids
            ):
                return None
            first, second = ids
            sign = self._parallel_distance_sign(
                layout.line(layout.values, first), layout.line(layout.values, second)
            )
            if sign is None:
                return None
            target = float(dimension.value)
            if not isfinite(target) or target < 0.0:
                return None
            return (
                lambda vector, first=first, second=second, sign=sign, target=target: (
                    self._signed_parallel_distance(
                        layout.line(vector, first), layout.line(vector, second)
                    )
                    - sign * target
                ),
            )

        if measurement_type in {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"} and len(ids) == 1:
            if dimension.unit != "mm" or not isinstance(entities.get(ids[0]), Circle):
                return None
            entity_id = ids[0]
            target = float(dimension.value)
            if not isfinite(target) or target <= 0.0:
                return None
            return (
                lambda vector, entity_id=entity_id, target=target: (
                    2.0 * layout.round(vector, entity_id)[2] - target
                ),
            )

        if measurement_type == "RADIUS" and len(ids) == 1:
            if dimension.unit != "mm" or not isinstance(entities.get(ids[0]), (Circle, Arc)):
                return None
            entity_id = ids[0]
            target = float(dimension.value)
            if not isfinite(target) or target <= 0.0:
                return None
            return (
                lambda vector, entity_id=entity_id, target=target: (
                    layout.round(vector, entity_id)[2] - target
                ),
            )

        if measurement_type == "CENTER_DISTANCE" and len(ids) == 2:
            if dimension.unit != "mm" or not all(
                isinstance(entities.get(entity_id), Circle) for entity_id in ids
            ):
                return None
            first, second = ids
            target = float(dimension.value)
            if not isfinite(target) or target < 0.0:
                return None
            if target <= self.degenerate_epsilon:
                return (
                    lambda vector, first=first, second=second: (
                        layout.round(vector, first)[0] - layout.round(vector, second)[0]
                    ),
                    lambda vector, first=first, second=second: (
                        layout.round(vector, first)[1] - layout.round(vector, second)[1]
                    ),
                )
            return (
                lambda vector, first=first, second=second, target=target: (
                    hypot(
                        layout.round(vector, first)[0] - layout.round(vector, second)[0],
                        layout.round(vector, first)[1] - layout.round(vector, second)[1],
                    )
                    - target
                ),
            )

        return None

    def _coincident_equations(
        self,
        first_id: str,
        second_id: str,
        entities: dict[str, GeometryPrimitive],
        layout: _ParameterLayout,
    ) -> tuple[_Equation, ...] | None:
        first = entities[first_id]
        second = entities[second_id]
        if isinstance(first, PointEntity) and isinstance(second, PointEntity):
            return (
                lambda vector, first_id=first_id, second_id=second_id: (
                    layout.point(vector, first_id)[0] - layout.point(vector, second_id)[0]
                ),
                lambda vector, first_id=first_id, second_id=second_id: (
                    layout.point(vector, first_id)[1] - layout.point(vector, second_id)[1]
                ),
            )

        witnesses: list[tuple[float, _Equation]] = []
        for source_id, target_id in ((first_id, second_id), (second_id, first_id)):
            target = entities[target_id]
            if isinstance(target, PointEntity):
                continue
            for ordinal in layout.contact_ordinals(source_id):
                point = layout.endpoint(layout.values, source_id, ordinal)
                built = self._point_on_entity_equation(
                    source_id,
                    ordinal,
                    target_id,
                    target,
                    layout,
                )
                if built is None:
                    continue
                residual = self._point_entity_distance(point, target)
                if isfinite(residual):
                    witnesses.append((residual, built))

        if not witnesses:
            return None
        witnesses.sort(key=lambda item: item[0])
        if len(witnesses) > 1 and abs(witnesses[1][0] - witnesses[0][0]) <= self.ambiguity_tolerance_mm:
            return None
        return (witnesses[0][1],)

    def _point_on_entity_equation(
        self,
        source_id: str,
        ordinal: int,
        target_id: str,
        target: GeometryPrimitive,
        layout: _ParameterLayout,
    ) -> _Equation | None:
        if isinstance(target, Line):
            return lambda vector, source_id=source_id, ordinal=ordinal, target_id=target_id: self._point_line_cross(
                layout.endpoint(vector, source_id, ordinal), layout.line(vector, target_id)
            )
        if isinstance(target, (Circle, Arc)):
            return lambda vector, source_id=source_id, ordinal=ordinal, target_id=target_id: self._point_round_residual_sq(
                layout.endpoint(vector, source_id, ordinal), layout.round(vector, target_id)
            )
        return None

    def _line_round_tangent_equation(
        self,
        line_id: str,
        round_id: str,
        layout: _ParameterLayout,
    ) -> _Equation:
        def equation(vector: tuple[float, ...]) -> float:
            sx, sy, ex, ey = layout.line(vector, line_id)
            cx, cy, radius = layout.round(vector, round_id)
            dx, dy = ex - sx, ey - sy
            length_sq = dx * dx + dy * dy
            if length_sq <= self.degenerate_epsilon:
                return float("nan")
            cross = dx * (cy - sy) - dy * (cx - sx)
            return cross * cross - radius * radius * length_sq

        return equation

    def _round_round_tangent_equation(
        self,
        first_id: str,
        second_id: str,
        layout: _ParameterLayout,
    ) -> _Equation:
        first = layout.round(layout.values, first_id)
        second = layout.round(layout.values, second_id)
        center_distance = hypot(first[0] - second[0], first[1] - second[1])
        external_error = abs(center_distance - (first[2] + second[2]))
        internal_error = abs(center_distance - abs(first[2] - second[2]))
        internal = internal_error < external_error

        def equation(vector: tuple[float, ...]) -> float:
            ax, ay, ar = layout.round(vector, first_id)
            bx, by, br = layout.round(vector, second_id)
            distance_sq = (ax - bx) ** 2 + (ay - by) ** 2
            radius_term = (ar - br) if internal else (ar + br)
            return distance_sq - radius_term * radius_term

        return equation

    def _symmetry_equations(
        self,
        first_id: str,
        second_id: str,
        axis_id: str,
        layout: _ParameterLayout,
        *,
        with_radius: bool,
    ) -> tuple[_Equation, ...]:
        def first_point(vector: tuple[float, ...]) -> tuple[float, float]:
            return (
                layout.round(vector, first_id)[:2]
                if with_radius
                else layout.point(vector, first_id)
            )

        def second_point(vector: tuple[float, ...]) -> tuple[float, float]:
            return (
                layout.round(vector, second_id)[:2]
                if with_radius
                else layout.point(vector, second_id)
            )

        def reflected(vector: tuple[float, ...]) -> tuple[float, float]:
            return self._reflect_point(first_point(vector), layout.line(vector, axis_id))

        equations: list[_Equation] = [
            lambda vector: reflected(vector)[0] - second_point(vector)[0],
            lambda vector: reflected(vector)[1] - second_point(vector)[1],
        ]
        if with_radius:
            equations.append(
                lambda vector: layout.round(vector, first_id)[2]
                - layout.round(vector, second_id)[2]
            )
        return tuple(equations)

    def _jacobian(
        self,
        equations: list[_Equation],
        vector: tuple[float, ...],
    ) -> list[list[float]]:
        if not equations:
            return []
        baseline = [equation(vector) for equation in equations]
        if any(not isfinite(value) for value in baseline):
            raise ValueError(
                "constraint-freedom equations are non-finite at the current geometry; diagnosis fails closed"
            )

        result = [[0.0 for _ in vector] for _ in equations]
        for column, value in enumerate(vector):
            step = self.finite_difference_step * max(1.0, abs(value))
            plus = list(vector)
            minus = list(vector)
            plus[column] += step
            minus[column] -= step
            plus_vector = tuple(plus)
            minus_vector = tuple(minus)
            for row, equation in enumerate(equations):
                high = equation(plus_vector)
                low = equation(minus_vector)
                if not isfinite(high) or not isfinite(low):
                    raise ValueError(
                        "constraint-freedom finite difference crossed unsupported/degenerate geometry"
                    )
                result[row][column] = (high - low) / (2.0 * step)
        return result

    @staticmethod
    def _normalize_rows(matrix: list[list[float]]) -> list[list[float]]:
        normalized: list[list[float]] = []
        for row in matrix:
            scale = max((abs(value) for value in row), default=0.0)
            if scale == 0.0:
                normalized.append(list(row))
            else:
                normalized.append([value / scale for value in row])
        return normalized

    def _matrix_rank(self, matrix: list[list[float]]) -> int:
        if not matrix:
            return 0
        work = [list(row) for row in matrix]
        rows = len(work)
        columns = len(work[0]) if rows else 0
        pivot_row = 0
        for column in range(columns):
            pivot = max(range(pivot_row, rows), key=lambda row: abs(work[row][column]), default=pivot_row)
            if pivot_row >= rows or abs(work[pivot][column]) <= self.rank_tolerance:
                continue
            work[pivot_row], work[pivot] = work[pivot], work[pivot_row]
            pivot_value = work[pivot_row][column]
            for index in range(column, columns):
                work[pivot_row][index] /= pivot_value
            for row in range(rows):
                if row == pivot_row:
                    continue
                factor = work[row][column]
                if abs(factor) <= self.rank_tolerance:
                    continue
                for index in range(column, columns):
                    work[row][index] -= factor * work[pivot_row][index]
            pivot_row += 1
            if pivot_row == rows:
                break
        return pivot_row

    def _frame_freedom_rank(
        self,
        layout: _ParameterLayout,
        normalized_jacobian: list[list[float]],
    ) -> int:
        modes = self._rigid_body_modes(layout)
        null_modes = [
            mode
            for mode in modes
            if self._mode_is_null(mode, normalized_jacobian)
        ]
        return self._matrix_rank([list(mode) for mode in null_modes])

    def _rigid_body_modes(self, layout: _ParameterLayout) -> tuple[tuple[float, ...], ...]:
        tx = [0.0] * len(layout.values)
        ty = [0.0] * len(layout.values)
        rotation = [0.0] * len(layout.values)
        angle_rate = 180.0 / pi

        for entity_id, slot in layout.slots.items():
            if slot.kind == "POINT":
                x, y = layout.point(layout.values, entity_id)
                tx[slot.offset] = 1.0
                ty[slot.offset + 1] = 1.0
                rotation[slot.offset] = -y
                rotation[slot.offset + 1] = x
            elif slot.kind == "LINE":
                sx, sy, ex, ey = layout.line(layout.values, entity_id)
                for x_index in (slot.offset, slot.offset + 2):
                    tx[x_index] = 1.0
                for y_index in (slot.offset + 1, slot.offset + 3):
                    ty[y_index] = 1.0
                rotation[slot.offset] = -sy
                rotation[slot.offset + 1] = sx
                rotation[slot.offset + 2] = -ey
                rotation[slot.offset + 3] = ex
            elif slot.kind in {"CIRCLE", "ARC"}:
                cx, cy, _ = layout.round(layout.values, entity_id)
                tx[slot.offset] = 1.0
                ty[slot.offset + 1] = 1.0
                rotation[slot.offset] = -cy
                rotation[slot.offset + 1] = cx
                if slot.kind == "ARC":
                    rotation[slot.offset + 3] = angle_rate
                    rotation[slot.offset + 4] = angle_rate

        return tuple(tuple(mode) for mode in (tx, ty, rotation))

    def _mode_is_null(
        self,
        mode: tuple[float, ...],
        jacobian: list[list[float]],
    ) -> bool:
        if not any(abs(value) > self.rank_tolerance for value in mode):
            return False
        for row in jacobian:
            residual = sum(value * delta for value, delta in zip(row, mode))
            scale = max(1.0, sum(abs(value * delta) for value, delta in zip(row, mode)))
            if abs(residual) > self.rank_tolerance * 100.0 * scale:
                return False
        return True

    def _indeterminate(
        self,
        variable_count: int,
        equations: tuple[_Equation, ...] | list[_Equation],
        issues: list[ConstraintFreedomIssue],
        *,
        unsupported_constraints: tuple[str, ...] = (),
        unsupported_dimensions: tuple[str, ...] = (),
    ) -> ConstraintFreedomDiagnosis:
        return ConstraintFreedomDiagnosis(
            status="INDETERMINATE",
            variable_count=variable_count,
            supported_equation_count=len(equations),
            supported_rank=0,
            degrees_of_freedom=None,
            frame_degrees_of_freedom=None,
            internal_degrees_of_freedom=None,
            issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
            unsupported_constraint_ids=unsupported_constraints,
            unsupported_dimension_ids=unsupported_dimensions,
        )

    @staticmethod
    def _conflicting(
        variable_count: int,
        issues: list[ConstraintFreedomIssue],
    ) -> ConstraintFreedomDiagnosis:
        return ConstraintFreedomDiagnosis(
            status="CONFLICTING",
            variable_count=variable_count,
            supported_equation_count=0,
            supported_rank=0,
            degrees_of_freedom=None,
            frame_degrees_of_freedom=None,
            internal_degrees_of_freedom=None,
            issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
        )

    @staticmethod
    def _line_cross(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> float:
        ax, ay = first[2] - first[0], first[3] - first[1]
        bx, by = second[2] - second[0], second[3] - second[1]
        return ax * by - ay * bx

    @staticmethod
    def _line_dot(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> float:
        ax, ay = first[2] - first[0], first[3] - first[1]
        bx, by = second[2] - second[0], second[3] - second[1]
        return ax * bx + ay * by

    @staticmethod
    def _line_length_sq(line: tuple[float, float, float, float]) -> float:
        return (line[2] - line[0]) ** 2 + (line[3] - line[1]) ** 2

    @staticmethod
    def _point_line_cross(
        point: tuple[float, float],
        line: tuple[float, float, float, float],
    ) -> float:
        sx, sy, ex, ey = line
        return (ex - sx) * (point[1] - sy) - (ey - sy) * (point[0] - sx)

    @staticmethod
    def _point_round_residual_sq(
        point: tuple[float, float],
        round_geometry: tuple[float, float, float],
    ) -> float:
        cx, cy, radius = round_geometry
        return (point[0] - cx) ** 2 + (point[1] - cy) ** 2 - radius * radius

    def _point_entity_distance(
        self,
        point: tuple[float, float],
        entity: GeometryPrimitive,
    ) -> float:
        if isinstance(entity, Line):
            dx = entity.end.x - entity.start.x
            dy = entity.end.y - entity.start.y
            length = hypot(dx, dy)
            if length <= self.degenerate_epsilon:
                return float("inf")
            return abs(dx * (point[1] - entity.start.y) - dy * (point[0] - entity.start.x)) / length
        if isinstance(entity, (Circle, Arc)):
            return abs(hypot(point[0] - entity.center.x, point[1] - entity.center.y) - entity.radius)
        return float("inf")

    def _signed_parallel_distance(
        self,
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> float:
        sx, sy, ex, ey = first
        dx, dy = ex - sx, ey - sy
        length = hypot(dx, dy)
        if length <= self.degenerate_epsilon:
            return float("nan")
        return (dx * (second[1] - sy) - dy * (second[0] - sx)) / length

    def _parallel_distance_sign(
        self,
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> float | None:
        first_length = hypot(first[2] - first[0], first[3] - first[1])
        second_length = hypot(second[2] - second[0], second[3] - second[1])
        if first_length <= self.degenerate_epsilon or second_length <= self.degenerate_epsilon:
            return None
        normalized_cross = abs(self._line_cross(first, second)) / (first_length * second_length)
        if normalized_cross > 1e-6:
            return None
        signed = self._signed_parallel_distance(first, second)
        if not isfinite(signed):
            return None
        return -1.0 if signed < 0.0 else 1.0

    @staticmethod
    def _reflect_point(
        point: tuple[float, float],
        axis: tuple[float, float, float, float],
    ) -> tuple[float, float]:
        sx, sy, ex, ey = axis
        dx, dy = ex - sx, ey - sy
        length_sq = dx * dx + dy * dy
        if length_sq == 0.0:
            return float("nan"), float("nan")
        parameter = ((point[0] - sx) * dx + (point[1] - sy) * dy) / length_sq
        foot_x = sx + parameter * dx
        foot_y = sy + parameter * dy
        return 2.0 * foot_x - point[0], 2.0 * foot_y - point[1]
