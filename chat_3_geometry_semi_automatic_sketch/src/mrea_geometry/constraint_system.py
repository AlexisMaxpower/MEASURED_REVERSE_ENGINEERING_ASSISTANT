from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from .constraints import ConstraintResolution, ResolvedConstraint
from .models import Arc, Circle, GeometryDraft, GeometryPrimitive, Line

ConstraintSystemStatus = Literal["CONSISTENT", "REDUNDANT", "CONFLICTING"]
_WORLD_HORIZONTAL = "__MREA_WORLD_HORIZONTAL__"


@dataclass(frozen=True, slots=True)
class ConstraintSystemIssue:
    """Read-only whole-system diagnostic with deterministic traceability."""

    issue_id: str
    code: str
    message: str
    constraint_ids: tuple[str, ...]
    entity_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        result = {
            "issue_id": self.issue_id,
            "code": self.code,
            "message": self.message,
            "constraint_ids": list(self.constraint_ids),
        }
        if self.entity_ids:
            result["entity_ids"] = list(self.entity_ids)
        return result


@dataclass(frozen=True, slots=True)
class ConstraintSystemDiagnosis:
    """Structural consistency result without claiming full constraint/DOF closure."""

    status: ConstraintSystemStatus
    issues: tuple[ConstraintSystemIssue, ...]
    redundant_constraint_ids: tuple[str, ...]
    conflicting_constraint_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "issues": [item.to_dict() for item in self.issues],
            "redundant_constraint_ids": list(self.redundant_constraint_ids),
            "conflicting_constraint_ids": list(self.conflicting_constraint_ids),
        }


class _RelationGraph:
    """Accepted relation graph with XOR parity and deterministic path evidence."""

    def __init__(self) -> None:
        self._adjacency: dict[str, list[tuple[str, int, str]]] = {}

    def add(self, first: str, second: str, parity: int, constraint_id: str) -> None:
        self._adjacency.setdefault(first, []).append((second, parity, constraint_id))
        self._adjacency.setdefault(second, []).append((first, parity, constraint_id))

    def path(self, first: str, second: str) -> tuple[int, tuple[str, ...]] | None:
        if first == second:
            return 0, ()
        queue: deque[tuple[str, int, tuple[str, ...]]] = deque([(first, 0, ())])
        visited = {first}
        while queue:
            node, parity, constraint_ids = queue.popleft()
            neighbors = sorted(
                self._adjacency.get(node, ()),
                key=lambda item: (item[0], item[2], item[1]),
            )
            for neighbor, edge_parity, constraint_id in neighbors:
                if neighbor in visited:
                    continue
                next_parity = parity ^ edge_parity
                next_ids = constraint_ids + (constraint_id,)
                if neighbor == second:
                    return next_parity, next_ids
                visited.add(neighbor)
                queue.append((neighbor, next_parity, next_ids))
        return None


class ConstraintSystemAnalyzer:
    """Diagnose supported global redundancy/conflicts without moving geometry.

    The analyzer consumes already-promoted constraints. It intentionally does not alter the
    resolution, infer missing constraints, solve degrees of freedom, or rewrite measurement
    truth. Unsupported logical combinations are left unclassified rather than guessed.
    """

    _UNORDERED_PAIR_KINDS = {
        "COINCIDENT",
        "PARALLEL",
        "PERPENDICULAR",
        "TANGENT",
        "CONCENTRIC",
        "EQUAL",
    }

    def analyze(
        self,
        draft: GeometryDraft,
        resolution: ConstraintResolution,
    ) -> ConstraintSystemDiagnosis:
        entities = {item.entity_id: item for item in draft.entities}
        ordered = tuple(
            sorted(
                resolution.constraints,
                key=lambda item: (item.constraint_id, item.kind, item.entity_ids),
            )
        )

        issues: list[ConstraintSystemIssue] = []
        redundant: set[str] = set()
        conflicting: set[str] = set()

        duplicate_ids = self._duplicate_constraint_ids(ordered)
        for constraint_id in duplicate_ids:
            conflicting.add(constraint_id)
            issues.append(
                ConstraintSystemIssue(
                    issue_id=f"CS-DUPLICATE-ID-{constraint_id}",
                    code="CONSTRAINT_SYSTEM_DUPLICATE_CONSTRAINT_ID",
                    message=(
                        "Constraint system contains more than one relation with the same "
                        "constraint_id; global diagnosis fails closed."
                    ),
                    constraint_ids=(constraint_id,),
                )
            )

        valid: list[ResolvedConstraint] = []
        for constraint in ordered:
            missing = tuple(sorted(set(constraint.entity_ids) - entities.keys()))
            if missing:
                conflicting.add(constraint.constraint_id)
                issues.append(
                    ConstraintSystemIssue(
                        issue_id=f"CS-MISSING-{constraint.constraint_id}",
                        code="CONSTRAINT_SYSTEM_ENTITY_MISSING",
                        message=(
                            "Published constraint references geometry absent from the analyzed draft."
                        ),
                        constraint_ids=(constraint.constraint_id,),
                        entity_ids=missing,
                    )
                )
                continue
            if constraint.constraint_id not in duplicate_ids:
                valid.append(constraint)

        unique = self._mark_semantic_duplicates(valid, redundant, issues)
        by_id = {constraint.constraint_id: constraint for constraint in unique}

        self._analyze_line_orientation(
            unique,
            entities=entities,
            by_id=by_id,
            redundant=redundant,
            conflicting=conflicting,
            issues=issues,
        )
        equivalence_graphs = self._analyze_equivalence_relations(
            unique,
            entities=entities,
            by_id=by_id,
            redundant=redundant,
            issues=issues,
        )
        self._analyze_round_tangency_conflicts(
            unique,
            entities=entities,
            by_id=by_id,
            concentric_graph=equivalence_graphs.get(("CONCENTRIC", "ROUND_CENTER")),
            conflicting=conflicting,
            issues=issues,
        )

        if conflicting:
            status: ConstraintSystemStatus = "CONFLICTING"
        elif redundant:
            status = "REDUNDANT"
        else:
            status = "CONSISTENT"

        return ConstraintSystemDiagnosis(
            status=status,
            issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
            redundant_constraint_ids=tuple(sorted(redundant)),
            conflicting_constraint_ids=tuple(sorted(conflicting)),
        )

    @staticmethod
    def _duplicate_constraint_ids(
        constraints: tuple[ResolvedConstraint, ...],
    ) -> tuple[str, ...]:
        counts: dict[str, int] = {}
        for constraint in constraints:
            counts[constraint.constraint_id] = counts.get(constraint.constraint_id, 0) + 1
        return tuple(sorted(key for key, count in counts.items() if count > 1))

    def _mark_semantic_duplicates(
        self,
        constraints: list[ResolvedConstraint],
        redundant: set[str],
        issues: list[ConstraintSystemIssue],
    ) -> tuple[ResolvedConstraint, ...]:
        seen: dict[tuple[str, tuple[str, ...]], ResolvedConstraint] = {}
        unique: list[ResolvedConstraint] = []

        for constraint in constraints:
            signature = self._signature(constraint)
            previous = seen.get(signature)
            if previous is None:
                seen[signature] = constraint
                unique.append(constraint)
                continue
            redundant.add(constraint.constraint_id)
            issues.append(
                ConstraintSystemIssue(
                    issue_id=f"CS-REDUNDANT-DUPLICATE-{constraint.constraint_id}",
                    code="CONSTRAINT_SYSTEM_REDUNDANT_DUPLICATE",
                    message=(
                        "Constraint repeats a previously published semantic relation and adds "
                        "no structural information."
                    ),
                    constraint_ids=(previous.constraint_id, constraint.constraint_id),
                    entity_ids=self._normalized_entity_ids(constraint),
                )
            )

        return tuple(unique)

    def _analyze_line_orientation(
        self,
        constraints: tuple[ResolvedConstraint, ...],
        *,
        entities: dict[str, GeometryPrimitive],
        by_id: dict[str, ResolvedConstraint],
        redundant: set[str],
        conflicting: set[str],
        issues: list[ConstraintSystemIssue],
    ) -> None:
        graph = _RelationGraph()
        for constraint in constraints:
            relation = self._orientation_relation(constraint, entities)
            if relation is None:
                continue
            first, second, required_parity = relation
            path = graph.path(first, second)
            if path is None:
                graph.add(first, second, required_parity, constraint.constraint_id)
                continue

            implied_parity, supporting_ids = path
            evidence_ids = tuple(sorted(set(supporting_ids + (constraint.constraint_id,))))
            entity_ids = self._entity_ids_for_constraints(evidence_ids, by_id)
            if implied_parity == required_parity:
                redundant.add(constraint.constraint_id)
                issues.append(
                    ConstraintSystemIssue(
                        issue_id=f"CS-REDUNDANT-ORIENTATION-{constraint.constraint_id}",
                        code="CONSTRAINT_SYSTEM_REDUNDANT_ORIENTATION",
                        message=(
                            "Line orientation relation is already implied by the accepted "
                            "HORIZONTAL/VERTICAL/PARALLEL/PERPENDICULAR relation graph."
                        ),
                        constraint_ids=evidence_ids,
                        entity_ids=entity_ids,
                    )
                )
                continue

            conflicting.update(evidence_ids)
            issues.append(
                ConstraintSystemIssue(
                    issue_id=f"CS-CONFLICT-ORIENTATION-{constraint.constraint_id}",
                    code="CONSTRAINT_SYSTEM_CONFLICTING_ORIENTATION",
                    message=(
                        "Line orientation relation contradicts the parity implied by the accepted "
                        "HORIZONTAL/VERTICAL/PARALLEL/PERPENDICULAR relation graph."
                    ),
                    constraint_ids=evidence_ids,
                    entity_ids=entity_ids,
                )
            )

    @staticmethod
    def _orientation_relation(
        constraint: ResolvedConstraint,
        entities: dict[str, GeometryPrimitive],
    ) -> tuple[str, str, int] | None:
        if constraint.kind in {"HORIZONTAL", "VERTICAL"} and len(constraint.entity_ids) == 1:
            entity_id = constraint.entity_ids[0]
            if not isinstance(entities.get(entity_id), Line):
                return None
            parity = 0 if constraint.kind == "HORIZONTAL" else 1
            return entity_id, _WORLD_HORIZONTAL, parity

        if constraint.kind in {"PARALLEL", "PERPENDICULAR"} and len(constraint.entity_ids) == 2:
            first, second = constraint.entity_ids
            if not isinstance(entities.get(first), Line) or not isinstance(entities.get(second), Line):
                return None
            parity = 0 if constraint.kind == "PARALLEL" else 1
            return first, second, parity
        return None

    def _analyze_equivalence_relations(
        self,
        constraints: tuple[ResolvedConstraint, ...],
        *,
        entities: dict[str, GeometryPrimitive],
        by_id: dict[str, ResolvedConstraint],
        redundant: set[str],
        issues: list[ConstraintSystemIssue],
    ) -> dict[tuple[str, str], _RelationGraph]:
        graphs: dict[tuple[str, str], _RelationGraph] = {}
        for constraint in constraints:
            domain = self._equivalence_domain(constraint, entities)
            if domain is None:
                continue
            key = (constraint.kind, domain)
            graph = graphs.setdefault(key, _RelationGraph())
            first, second = constraint.entity_ids
            path = graph.path(first, second)
            if path is None:
                graph.add(first, second, 0, constraint.constraint_id)
                continue

            _, supporting_ids = path
            redundant.add(constraint.constraint_id)
            evidence_ids = tuple(sorted(set(supporting_ids + (constraint.constraint_id,))))
            issues.append(
                ConstraintSystemIssue(
                    issue_id=f"CS-REDUNDANT-CYCLE-{constraint.constraint_id}",
                    code="CONSTRAINT_SYSTEM_REDUNDANT_CYCLE",
                    message=(
                        "Constraint closes an equivalence-relation cycle already implied by "
                        "earlier deterministic relations."
                    ),
                    constraint_ids=evidence_ids,
                    entity_ids=self._entity_ids_for_constraints(evidence_ids, by_id),
                )
            )
        return graphs

    def _analyze_round_tangency_conflicts(
        self,
        constraints: tuple[ResolvedConstraint, ...],
        *,
        entities: dict[str, GeometryPrimitive],
        by_id: dict[str, ResolvedConstraint],
        concentric_graph: _RelationGraph | None,
        conflicting: set[str],
        issues: list[ConstraintSystemIssue],
    ) -> None:
        if concentric_graph is None:
            return
        for constraint in constraints:
            if constraint.kind != "TANGENT" or len(constraint.entity_ids) != 2:
                continue
            first, second = constraint.entity_ids
            if not isinstance(entities.get(first), (Circle, Arc)) or not isinstance(
                entities.get(second), (Circle, Arc)
            ):
                continue
            path = concentric_graph.path(first, second)
            if path is None:
                continue
            _, supporting_ids = path
            evidence_ids = tuple(sorted(set(supporting_ids + (constraint.constraint_id,))))
            conflicting.update(evidence_ids)
            issues.append(
                ConstraintSystemIssue(
                    issue_id=f"CS-CONFLICT-ROUND-{constraint.constraint_id}",
                    code="CONSTRAINT_SYSTEM_CONFLICTING_ROUND_RELATION",
                    message=(
                        "Round entities are transitively CONCENTRIC while also constrained "
                        "TANGENT; positive-radius round geometry cannot satisfy both relations."
                    ),
                    constraint_ids=evidence_ids,
                    entity_ids=self._entity_ids_for_constraints(evidence_ids, by_id),
                )
            )

    @staticmethod
    def _equivalence_domain(
        constraint: ResolvedConstraint,
        entities: dict[str, GeometryPrimitive],
    ) -> str | None:
        if len(constraint.entity_ids) != 2:
            return None
        first = entities[constraint.entity_ids[0]]
        second = entities[constraint.entity_ids[1]]
        if constraint.kind == "CONCENTRIC":
            return (
                "ROUND_CENTER"
                if isinstance(first, (Circle, Arc)) and isinstance(second, (Circle, Arc))
                else None
            )
        if constraint.kind == "EQUAL":
            if isinstance(first, Line) and isinstance(second, Line):
                return "LINE_LENGTH"
            if isinstance(first, (Circle, Arc)) and isinstance(second, (Circle, Arc)):
                return "ROUND_RADIUS"
        return None

    @staticmethod
    def _entity_ids_for_constraints(
        constraint_ids: tuple[str, ...],
        by_id: dict[str, ResolvedConstraint],
    ) -> tuple[str, ...]:
        result: set[str] = set()
        for constraint_id in constraint_ids:
            constraint = by_id.get(constraint_id)
            if constraint is not None:
                result.update(constraint.entity_ids)
        return tuple(sorted(result))

    def _signature(self, constraint: ResolvedConstraint) -> tuple[str, tuple[str, ...]]:
        return constraint.kind, self._normalized_entity_ids(constraint)

    def _normalized_entity_ids(self, constraint: ResolvedConstraint) -> tuple[str, ...]:
        entity_ids = constraint.entity_ids
        if constraint.kind in self._UNORDERED_PAIR_KINDS and len(entity_ids) == 2:
            return tuple(sorted(entity_ids))
        if constraint.kind == "SYMMETRIC" and len(entity_ids) == 3:
            first, second, axis = entity_ids
            left, right = sorted((first, second))
            return left, right, axis
        return entity_ids
