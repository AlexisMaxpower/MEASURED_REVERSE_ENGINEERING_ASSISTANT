from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .constraint_satisfaction import ConstraintSatisfactionAnalyzer
from .models import Circle, ConstraintCandidate, DimensionBinding, GeometryDraft, Line

ConstraintStatus = Literal["DETECTED", "INFERRED"]


@dataclass(frozen=True, slots=True)
class ResolvedConstraint:
    """Constraint approved for canonical publication inside Chat 3."""

    constraint_id: str
    kind: str
    entity_ids: tuple[str, ...]
    status: ConstraintStatus
    confidence: float

    def to_canonical(self) -> dict:
        return {
            "constraint_id": self.constraint_id,
            "type": self.kind,
            "entity_ids": list(self.entity_ids),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ConstraintIssue:
    issue_id: str
    code: str
    message: str
    entity_ids: tuple[str, ...] = ()
    measurement_ids: tuple[str, ...] = ()

    def to_canonical(self) -> dict:
        result = {
            "unresolved_id": self.issue_id,
            "code": self.code,
            "message": self.message,
        }
        if self.entity_ids:
            result["entity_ids"] = list(self.entity_ids)
        if self.measurement_ids:
            result["measurement_ids"] = list(self.measurement_ids)
        return result


@dataclass(frozen=True, slots=True)
class ConstraintResolution:
    constraints: tuple[ResolvedConstraint, ...]
    issues: tuple[ConstraintIssue, ...]


class ConstraintResolver:
    """Promote deterministic geometry candidates without overriding measurement truth.

    The resolver intentionally does not move geometry. It decides which already-observed
    relations are safe to publish in SketchPackage v1 and which must remain unresolved.
    """

    def __init__(
        self,
        *,
        minimum_confidence: float = 0.95,
        measurement_tolerance: float = 0.05,
        satisfaction_analyzer: ConstraintSatisfactionAnalyzer | None = None,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if measurement_tolerance < 0:
            raise ValueError("measurement_tolerance must be non-negative")
        self.minimum_confidence = minimum_confidence
        self.measurement_tolerance = measurement_tolerance
        self.satisfaction_analyzer = satisfaction_analyzer or ConstraintSatisfactionAnalyzer()

    def resolve(self, draft: GeometryDraft) -> ConstraintResolution:
        entities = {item.entity_id: item for item in draft.entities}
        candidates = self._deduplicate(draft.constraints)
        axis_by_entity = self._axis_map(candidates)
        verified_metrics = self._verified_metrics(draft.dimensions, entities)
        center_distances = self._verified_center_distances(draft.dimensions)

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

            effective_confidence = self._effective_confidence(candidate, entities)
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

            satisfaction = self.satisfaction_analyzer.analyze(candidate, entities)
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

            if self._is_axis_redundant(candidate, axis_by_entity):
                continue

            conflict = self._measurement_conflict(
                candidate,
                verified_metrics=verified_metrics,
                center_distances=center_distances,
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

    @staticmethod
    def _effective_confidence(
        candidate: ConstraintCandidate,
        entities: dict[str, object],
    ) -> float:
        values = [candidate.confidence]
        for entity_id in candidate.entity_ids:
            confidence = getattr(entities[entity_id], "confidence", None)
            if confidence is not None:
                values.append(float(confidence))
        return min(values)

    @staticmethod
    def _deduplicate(
        candidates: tuple[ConstraintCandidate, ...],
    ) -> tuple[ConstraintCandidate, ...]:
        by_signature: dict[tuple[str, tuple[str, ...]], ConstraintCandidate] = {}
        for candidate in sorted(candidates, key=lambda item: item.constraint_id):
            signature = (candidate.kind, tuple(sorted(candidate.entity_ids)))
            by_signature.setdefault(signature, candidate)
        return tuple(sorted(by_signature.values(), key=lambda item: item.constraint_id))

    @staticmethod
    def _axis_map(
        candidates: tuple[ConstraintCandidate, ...],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for candidate in candidates:
            if candidate.kind in {"HORIZONTAL", "VERTICAL"} and len(candidate.entity_ids) == 1:
                result[candidate.entity_ids[0]] = candidate.kind
        return result

    @staticmethod
    def _is_axis_redundant(
        candidate: ConstraintCandidate,
        axis_by_entity: dict[str, str],
    ) -> bool:
        if len(candidate.entity_ids) != 2:
            return False
        first, second = candidate.entity_ids
        first_axis = axis_by_entity.get(first)
        second_axis = axis_by_entity.get(second)
        if first_axis is None or second_axis is None:
            return False
        if candidate.kind == "PARALLEL":
            return first_axis == second_axis
        if candidate.kind == "PERPENDICULAR":
            return {first_axis, second_axis} == {"HORIZONTAL", "VERTICAL"}
        return False

    @staticmethod
    def _verified_metrics(
        dimensions: tuple[DimensionBinding, ...],
        entities: dict[str, object],
    ) -> dict[str, list[tuple[str, float, str]]]:
        result: dict[str, list[tuple[str, float, str]]] = {}
        for dimension in dimensions:
            if not dimension.verified or len(dimension.target_entity_ids) != 1:
                continue
            entity_id = dimension.target_entity_ids[0]
            entity = entities.get(entity_id)
            metric: tuple[str, float] | None = None
            if isinstance(entity, Circle):
                if dimension.measurement_type in {"DIAMETER_EXTERNAL", "DIAMETER_INTERNAL"}:
                    metric = ("RADIUS", dimension.value / 2.0)
                elif dimension.measurement_type == "RADIUS":
                    metric = ("RADIUS", dimension.value)
            elif isinstance(entity, Line) and dimension.measurement_type in {
                "LINEAR_EXTERNAL",
                "LINEAR_INTERNAL",
                "THICKNESS",
                "SLOT_WIDTH",
            }:
                metric = ("LENGTH", dimension.value)
            if metric is not None:
                result.setdefault(entity_id, []).append(
                    (metric[0], metric[1], dimension.measurement_id)
                )
        return result

    @staticmethod
    def _verified_center_distances(
        dimensions: tuple[DimensionBinding, ...],
    ) -> dict[tuple[str, str], list[tuple[float, str]]]:
        result: dict[tuple[str, str], list[tuple[float, str]]] = {}
        for dimension in dimensions:
            if (
                dimension.verified
                and dimension.measurement_type == "CENTER_DISTANCE"
                and len(dimension.target_entity_ids) == 2
            ):
                key = tuple(sorted(dimension.target_entity_ids))
                result.setdefault(key, []).append((dimension.value, dimension.measurement_id))
        return result

    def _measurement_conflict(
        self,
        candidate: ConstraintCandidate,
        *,
        verified_metrics: dict[str, list[tuple[str, float, str]]],
        center_distances: dict[tuple[str, str], list[tuple[float, str]]],
    ) -> ConstraintIssue | None:
        if len(candidate.entity_ids) != 2:
            return None
        first, second = candidate.entity_ids

        if candidate.kind == "EQUAL":
            conflicts: list[tuple[str, str]] = []
            for left_kind, left_value, left_mid in verified_metrics.get(first, []):
                for right_kind, right_value, right_mid in verified_metrics.get(second, []):
                    if left_kind == right_kind and abs(left_value - right_value) > self.measurement_tolerance:
                        conflicts.append((left_mid, right_mid))
            if conflicts:
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

        if candidate.kind == "CONCENTRIC":
            key = tuple(sorted(candidate.entity_ids))
            conflicts = [
                (value, measurement_id)
                for value, measurement_id in center_distances.get(key, [])
                if abs(value) > self.measurement_tolerance
            ]
            if conflicts:
                return ConstraintIssue(
                    issue_id=f"U-{candidate.constraint_id}",
                    code="VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT",
                    message=(
                        "CONCENTRIC geometry candidate conflicts with a verified non-zero center "
                        "distance; verified measurement was preserved and the constraint was not published."
                    ),
                    entity_ids=key,
                    measurement_ids=tuple(sorted(item[1] for item in conflicts)),
                )

        return None
