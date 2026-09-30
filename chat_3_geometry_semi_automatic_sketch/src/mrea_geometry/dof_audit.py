from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .constraints import ConstraintResolution
from .models import Arc, Circle, GeometryDraft, Line, PointEntity

DofClassification = Literal[
    "DEFINITELY_UNDERCONSTRAINED",
    "NOT_PROVEN_UNDERCONSTRAINED",
    "INDETERMINATE_UNKNOWN_CONSTRAINT_ARITY",
]


@dataclass(frozen=True, slots=True)
class StructuralDofAudit:
    """Conservative structural degrees-of-freedom audit.

    This is deliberately not a CAD solver or Jacobian-rank proof. The audit counts the
    exact number of primitive parameters and an upper bound on scalar equations that
    the currently retained constraints and dimensions could impose.

    Therefore a positive ``remaining_dof_lower_bound`` proves that the sketch is still
    underconstrained. A zero lower bound does *not* prove that the sketch is fully
    constrained because equations can still be dependent or degenerate.
    """

    parameter_count: int
    constraint_equation_upper_bound: int
    dimension_equation_upper_bound: int
    total_equation_upper_bound: int
    remaining_dof_lower_bound: int | None
    classification: DofClassification
    entity_parameter_counts: tuple[tuple[str, int], ...]
    constraint_equation_counts: tuple[tuple[str, int], ...]
    dimension_ids: tuple[str, ...]
    unknown_constraint_ids: tuple[str, ...]


class StructuralDofAnalyzer:
    """Compute a fail-closed structural DOF lower bound without moving geometry."""

    _CONSTRAINT_MAX_SCALAR_EQUATIONS = {
        "HORIZONTAL": 1,
        "VERTICAL": 1,
        "PARALLEL": 1,
        "PERPENDICULAR": 1,
        "TANGENT": 1,
        "EQUAL": 1,
        "CONCENTRIC": 2,
        # Entity-level COINCIDENT does not identify the exact contact parameterization;
        # two equations is a safe upper bound for the supported 2D primitive family.
        "COINCIDENT": 2,
        # Point symmetry needs two equations; circle symmetry can additionally constrain
        # radius equality. Three is therefore the conservative supported-family maximum.
        "SYMMETRIC": 3,
    }

    def analyze(
        self,
        draft: GeometryDraft,
        resolution: ConstraintResolution,
    ) -> StructuralDofAudit:
        entity_counts = tuple(
            sorted(
                (
                    (entity.entity_id, self._entity_parameter_count(entity))
                    for entity in draft.entities
                ),
                key=lambda item: item[0],
            )
        )
        parameter_count = sum(count for _, count in entity_counts)

        constraint_counts: list[tuple[str, int]] = []
        unknown: list[str] = []
        for constraint in sorted(resolution.constraints, key=lambda item: item.constraint_id):
            equation_count = self._CONSTRAINT_MAX_SCALAR_EQUATIONS.get(constraint.kind)
            if equation_count is None:
                unknown.append(constraint.constraint_id)
                continue
            constraint_counts.append((constraint.constraint_id, equation_count))

        dimension_ids = tuple(
            sorted(dimension.dimension_id for dimension in draft.dimensions)
        )
        # Every supported canonical dimension contributes at most one scalar equation.
        dimension_equation_upper_bound = len(dimension_ids)
        constraint_equation_upper_bound = sum(count for _, count in constraint_counts)
        total_equation_upper_bound = (
            constraint_equation_upper_bound + dimension_equation_upper_bound
        )

        if unknown:
            remaining: int | None = None
            classification: DofClassification = (
                "INDETERMINATE_UNKNOWN_CONSTRAINT_ARITY"
            )
        else:
            remaining = max(0, parameter_count - total_equation_upper_bound)
            classification = (
                "DEFINITELY_UNDERCONSTRAINED"
                if remaining > 0
                else "NOT_PROVEN_UNDERCONSTRAINED"
            )

        return StructuralDofAudit(
            parameter_count=parameter_count,
            constraint_equation_upper_bound=constraint_equation_upper_bound,
            dimension_equation_upper_bound=dimension_equation_upper_bound,
            total_equation_upper_bound=total_equation_upper_bound,
            remaining_dof_lower_bound=remaining,
            classification=classification,
            entity_parameter_counts=entity_counts,
            constraint_equation_counts=tuple(constraint_counts),
            dimension_ids=dimension_ids,
            unknown_constraint_ids=tuple(sorted(unknown)),
        )

    @staticmethod
    def _entity_parameter_count(entity: object) -> int:
        if isinstance(entity, PointEntity):
            return 2
        if isinstance(entity, Line):
            return 4
        if isinstance(entity, Circle):
            return 3
        if isinstance(entity, Arc):
            return 5
        raise TypeError(f"unsupported geometry entity for DOF audit: {type(entity).__name__}")
