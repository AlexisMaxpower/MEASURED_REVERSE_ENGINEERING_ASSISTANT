from __future__ import annotations

from dataclasses import replace
from math import isfinite
from typing import Protocol

from .constraint_confidence import ConstraintConfidenceModel
from .constraint_satisfaction import ConstraintSatisfaction, ConstraintSatisfactionAnalyzer
from .constraints import ConstraintIssue, ConstraintResolution, ConstraintResolver, ResolvedConstraint
from .models import (
    Circle,
    ConstraintCandidate,
    DimensionBinding,
    GeometryDraft,
    GeometryPrimitive,
    Line,
)


class ConstraintTolerancePolicy(Protocol):
    """Optional post-residual policy used by an uncertainty-aware resolver."""

    def apply(
        self,
        candidate: ConstraintCandidate,
        satisfaction: ConstraintSatisfaction,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
    ) -> ConstraintSatisfaction: ...


class MeasurementContradictionPolicy(Protocol):
    """Policy boundary for verified-measurement contradiction checks."""

    def conflict(
        self,
        candidate: ConstraintCandidate,
        *,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
        measurement_tolerance: float,
    ) -> ConstraintIssue | None: ...


class UncertaintyAwareConstraintTolerancePolicy:
    """Widen linear residual tolerance only from directly relevant verified uncertainty.

    The policy is deliberately narrow. It does not infer angular/contact uncertainty from
    unrelated dimensions. Missing uncertainty leaves the baseline satisfaction unchanged.
    """

    _LINEAR_TYPES = {
        "LINEAR_EXTERNAL",
        "LINEAR_INTERNAL",
        "THICKNESS",
        "SLOT_WIDTH",
    }
    _DIAMETER_TYPES = {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"}

    def __init__(self, *, uncertainty_scale: float = 1.0) -> None:
        if not isfinite(uncertainty_scale) or uncertainty_scale < 0.0:
            raise ValueError("uncertainty_scale must be a finite non-negative number")
        self.uncertainty_scale = float(uncertainty_scale)

    def apply(
        self,
        candidate: ConstraintCandidate,
        satisfaction: ConstraintSatisfaction,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
    ) -> ConstraintSatisfaction:
        if satisfaction.unit != "mm":
            return satisfaction
        if not isfinite(satisfaction.tolerance) or satisfaction.tolerance < 0.0:
            raise ValueError("constraint satisfaction tolerance must be finite and non-negative")

        applied_uncertainty = self._applied_uncertainty(
            candidate,
            dimensions=dimensions,
            entities=entities,
        )
        if applied_uncertainty is None:
            return satisfaction

        effective_tolerance = satisfaction.tolerance + self.uncertainty_scale * applied_uncertainty
        if not isfinite(effective_tolerance):
            raise ValueError("effective constraint tolerance must be finite")

        return replace(
            satisfaction,
            satisfied=satisfaction.residual <= effective_tolerance,
            tolerance=effective_tolerance,
        )

    def _applied_uncertainty(
        self,
        candidate: ConstraintCandidate,
        *,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
    ) -> float | None:
        if candidate.kind == "EQUAL":
            return self._equal_uncertainty(candidate, dimensions, entities)
        if candidate.kind == "CONCENTRIC":
            return self._concentric_uncertainty(candidate, dimensions)
        return None

    def _equal_uncertainty(
        self,
        candidate: ConstraintCandidate,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
    ) -> float | None:
        if len(candidate.entity_ids) != 2:
            return None
        first_id, second_id = candidate.entity_ids
        first = entities.get(first_id)
        second = entities.get(second_id)
        if first is None or second is None:
            return None

        first_uncertainty = self._intrinsic_uncertainty(first_id, first, dimensions)
        second_uncertainty = self._intrinsic_uncertainty(second_id, second, dimensions)
        if first_uncertainty is None or second_uncertainty is None:
            return None
        return first_uncertainty + second_uncertainty

    def _intrinsic_uncertainty(
        self,
        entity_id: str,
        entity: GeometryPrimitive,
        dimensions: tuple[DimensionBinding, ...],
    ) -> float | None:
        values: list[float] = []
        for dimension in dimensions:
            if not dimension.verified or dimension.target_entity_ids != (entity_id,):
                continue

            factor: float | None = None
            if isinstance(entity, Circle):
                if dimension.measurement_type == "RADIUS":
                    factor = 1.0
                elif dimension.measurement_type in self._DIAMETER_TYPES:
                    factor = 0.5
            elif isinstance(entity, Line) and dimension.measurement_type in self._LINEAR_TYPES:
                factor = 1.0

            if factor is None or dimension.uncertainty is None:
                continue
            values.append(self._validated_uncertainty(dimension) * factor)

        return min(values) if values else None

    def _concentric_uncertainty(
        self,
        candidate: ConstraintCandidate,
        dimensions: tuple[DimensionBinding, ...],
    ) -> float | None:
        if len(candidate.entity_ids) != 2:
            return None
        key = tuple(sorted(candidate.entity_ids))
        values: list[float] = []
        for dimension in dimensions:
            if (
                not dimension.verified
                or dimension.measurement_type != "CENTER_DISTANCE"
                or tuple(sorted(dimension.target_entity_ids)) != key
                or dimension.uncertainty is None
            ):
                continue
            values.append(self._validated_uncertainty(dimension))
        return min(values) if values else None

    @staticmethod
    def _validated_uncertainty(dimension: DimensionBinding) -> float:
        if dimension.unit != "mm":
            raise ValueError("relevant constraint uncertainty must use mm")
        uncertainty = dimension.uncertainty
        if uncertainty is None:
            raise ValueError("dimension uncertainty is required")
        if not isfinite(uncertainty) or uncertainty < 0.0:
            raise ValueError("dimension uncertainty must be a finite non-negative number")
        return float(uncertainty)


class UncertaintyAwareMeasurementContradictionPolicy:
    """Evaluate verified-measurement contradiction using explicit measurement uncertainty.

    Uncertainty may relax only the already-supported EQUAL intrinsic-metric and CONCENTRIC
    center-distance contradiction gates. Missing uncertainty preserves fixed baseline behavior.
    """

    _LINEAR_TYPES = {
        "LINEAR_EXTERNAL",
        "LINEAR_INTERNAL",
        "THICKNESS",
        "SLOT_WIDTH",
    }
    _DIAMETER_TYPES = {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"}

    def conflict(
        self,
        candidate: ConstraintCandidate,
        *,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
        measurement_tolerance: float,
    ) -> ConstraintIssue | None:
        if not isfinite(measurement_tolerance) or measurement_tolerance < 0.0:
            raise ValueError("measurement_tolerance must be a finite non-negative number")
        if len(candidate.entity_ids) != 2:
            return None
        if candidate.kind == "EQUAL":
            return self._equal_conflict(
                candidate,
                dimensions=dimensions,
                entities=entities,
                measurement_tolerance=measurement_tolerance,
            )
        if candidate.kind == "CONCENTRIC":
            return self._concentric_conflict(
                candidate,
                dimensions=dimensions,
                measurement_tolerance=measurement_tolerance,
            )
        return None

    def _equal_conflict(
        self,
        candidate: ConstraintCandidate,
        *,
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, GeometryPrimitive],
        measurement_tolerance: float,
    ) -> ConstraintIssue | None:
        first_id, second_id = candidate.entity_ids
        first = entities.get(first_id)
        second = entities.get(second_id)
        if first is None or second is None:
            return None

        left_metrics = self._verified_metrics(first_id, first, dimensions)
        right_metrics = self._verified_metrics(second_id, second, dimensions)
        conflicts: list[tuple[str, str]] = []

        for left_kind, left_value, left_uncertainty, left_mid in left_metrics:
            for right_kind, right_value, right_uncertainty, right_mid in right_metrics:
                if left_kind != right_kind:
                    continue
                allowance = measurement_tolerance
                if left_uncertainty is not None and right_uncertainty is not None:
                    allowance += left_uncertainty + right_uncertainty
                if abs(left_value - right_value) > allowance:
                    conflicts.append((left_mid, right_mid))

        if not conflicts:
            return None

        measurement_ids = tuple(sorted({mid for pair in conflicts for mid in pair}))
        return ConstraintIssue(
            issue_id=f"U-{candidate.constraint_id}",
            code="VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT",
            message=(
                "EQUAL geometry candidate conflicts with verified physical measurements; "
                "verified measurements were preserved and the constraint was not published."
            ),
            entity_ids=tuple(sorted(candidate.entity_ids)),
            measurement_ids=measurement_ids,
        )

    def _concentric_conflict(
        self,
        candidate: ConstraintCandidate,
        *,
        dimensions: tuple[DimensionBinding, ...],
        measurement_tolerance: float,
    ) -> ConstraintIssue | None:
        key = tuple(sorted(candidate.entity_ids))
        conflicts: list[str] = []

        for dimension in dimensions:
            if (
                not dimension.verified
                or dimension.measurement_type != "CENTER_DISTANCE"
                or tuple(sorted(dimension.target_entity_ids)) != key
            ):
                continue
            allowance = measurement_tolerance
            if dimension.uncertainty is not None:
                allowance += self._validated_uncertainty(dimension)
            if abs(dimension.value) > allowance:
                conflicts.append(dimension.measurement_id)

        if not conflicts:
            return None

        return ConstraintIssue(
            issue_id=f"U-{candidate.constraint_id}",
            code="VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT",
            message=(
                "CONCENTRIC geometry candidate conflicts with a verified non-zero center "
                "distance; verified measurement was preserved and the constraint was not published."
            ),
            entity_ids=key,
            measurement_ids=tuple(sorted(conflicts)),
        )

    def _verified_metrics(
        self,
        entity_id: str,
        entity: GeometryPrimitive,
        dimensions: tuple[DimensionBinding, ...],
    ) -> tuple[tuple[str, float, float | None, str], ...]:
        result: list[tuple[str, float, float | None, str]] = []
        for dimension in dimensions:
            if not dimension.verified or dimension.target_entity_ids != (entity_id,):
                continue

            metric_kind: str | None = None
            metric_value: float | None = None
            uncertainty_factor = 1.0

            if isinstance(entity, Circle):
                if dimension.measurement_type in self._DIAMETER_TYPES:
                    metric_kind = "RADIUS"
                    metric_value = dimension.value / 2.0
                    uncertainty_factor = 0.5
                elif dimension.measurement_type == "RADIUS":
                    metric_kind = "RADIUS"
                    metric_value = dimension.value
            elif isinstance(entity, Line) and dimension.measurement_type in self._LINEAR_TYPES:
                metric_kind = "LENGTH"
                metric_value = dimension.value

            if metric_kind is None or metric_value is None:
                continue

            metric_uncertainty: float | None = None
            if dimension.uncertainty is not None:
                metric_uncertainty = self._validated_uncertainty(dimension) * uncertainty_factor

            result.append(
                (
                    metric_kind,
                    float(metric_value),
                    metric_uncertainty,
                    dimension.measurement_id,
                )
            )

        return tuple(sorted(result, key=lambda item: (item[0], item[3], item[1])))

    @staticmethod
    def _validated_uncertainty(dimension: DimensionBinding) -> float:
        if dimension.unit != "mm":
            raise ValueError("relevant measurement contradiction uncertainty must use mm")
        uncertainty = dimension.uncertainty
        if uncertainty is None:
            raise ValueError("dimension uncertainty is required")
        if not isfinite(uncertainty) or uncertainty < 0.0:
            raise ValueError("dimension uncertainty must be a finite non-negative number")
        return float(uncertainty)


class UncertaintyAwareConstraintResolver(ConstraintResolver):
    """Explicit resolver variant with measurement-grounded uncertainty policies.

    The base ``ConstraintResolver`` remains unchanged. This resolver performs the same
    promotion gates in the same order, with opt-in uncertainty handling for geometric
    residual tolerance and verified-measurement contradiction decisions.
    """

    def __init__(
        self,
        *,
        minimum_confidence: float = 0.95,
        measurement_tolerance: float = 0.05,
        satisfaction_analyzer: ConstraintSatisfactionAnalyzer | None = None,
        confidence_model: ConstraintConfidenceModel | None = None,
        tolerance_policy: ConstraintTolerancePolicy | None = None,
        measurement_contradiction_policy: MeasurementContradictionPolicy | None = None,
    ) -> None:
        super().__init__(
            minimum_confidence=minimum_confidence,
            measurement_tolerance=measurement_tolerance,
            satisfaction_analyzer=satisfaction_analyzer,
            confidence_model=confidence_model,
        )
        self.tolerance_policy = tolerance_policy or UncertaintyAwareConstraintTolerancePolicy()
        self.measurement_contradiction_policy = (
            measurement_contradiction_policy or UncertaintyAwareMeasurementContradictionPolicy()
        )

    def resolve(self, draft: GeometryDraft) -> ConstraintResolution:
        entities = {item.entity_id: item for item in draft.entities}
        candidates = self._deduplicate(draft.constraints)
        axis_by_entity = self._axis_map(candidates)

        resolved: list[ResolvedConstraint] = []
        issues: list[ConstraintIssue] = []

        for candidate in candidates:
            missing = tuple(sorted(set(candidate.entity_ids) - entities.keys()))
            if missing:
                issues.append(
                    ConstraintIssue(
                        issue_id=f"U-{candidate.constraint_id}",
                        code="CONSTRAINT_ENTITY_MISSING",
                        message="Constraint candidate references geometry that is not present in the draft.",
                        entity_ids=missing,
                    )
                )
                continue

            satisfaction = self.satisfaction_analyzer.analyze(candidate, entities)
            satisfaction = self.tolerance_policy.apply(
                candidate,
                satisfaction,
                draft.dimensions,
                entities,
            )
            if not satisfaction.satisfied:
                issues.append(
                    ConstraintIssue(
                        issue_id=f"U-{candidate.constraint_id}",
                        code="UNSATISFIED_CONSTRAINT",
                        message=(
                            f"{candidate.kind} relation residual {satisfaction.residual:.6g} "
                            f"{satisfaction.unit} exceeds tolerance {satisfaction.tolerance:.6g} "
                            f"{satisfaction.unit}; relation was not published."
                        ),
                        entity_ids=candidate.entity_ids,
                    )
                )
                continue

            geometric_confidence = self.confidence_model.score(satisfaction).confidence
            effective_confidence = self._effective_confidence(
                candidate,
                entities,
                geometric_confidence=geometric_confidence,
            )
            if effective_confidence < self.minimum_confidence:
                issues.append(
                    ConstraintIssue(
                        issue_id=f"U-{candidate.constraint_id}",
                        code="CONSTRAINT_BELOW_PROMOTION_CONFIDENCE",
                        message=(
                            f"Constraint confidence {effective_confidence:.3f} is below "
                            f"promotion threshold {self.minimum_confidence:.3f}."
                        ),
                        entity_ids=candidate.entity_ids,
                    )
                )
                continue

            if self._is_axis_redundant(candidate, axis_by_entity):
                continue

            conflict = self.measurement_contradiction_policy.conflict(
                candidate,
                dimensions=draft.dimensions,
                entities=entities,
                measurement_tolerance=self.measurement_tolerance,
            )
            if conflict is not None:
                issues.append(conflict)
                continue

            resolved.append(
                ResolvedConstraint(
                    constraint_id=candidate.constraint_id,
                    kind=candidate.kind,
                    entity_ids=candidate.entity_ids,
                    status="INFERRED" if candidate.inferred else "DETECTED",
                    confidence=effective_confidence,
                )
            )

        return ConstraintResolution(
            constraints=tuple(sorted(resolved, key=lambda item: item.constraint_id)),
            issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
        )
