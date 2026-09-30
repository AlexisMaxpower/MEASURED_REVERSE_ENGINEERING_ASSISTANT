from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

from .constraints import ConstraintIssue, ConstraintResolution, ResolvedConstraint


@dataclass(frozen=True, slots=True)
class ConstraintSystemAnalysis:
    """Deterministic global diagnostics for an already-resolved constraint set."""

    resolution: ConstraintResolution
    redundant_constraint_ids: tuple[str, ...]
    rejected_constraint_ids: tuple[str, ...]


class _ParityDisjointSet:
    """Union-find with XOR parity between nodes.

    A relation parity of 0 means "same orientation class" and 1 means
    "perpendicular orientation class".
    """

    def __init__(self) -> None:
        self._parent: dict[Hashable, Hashable] = {}
        self._rank: dict[Hashable, int] = {}
        self._parity: dict[Hashable, int] = {}

    def _ensure(self, item: Hashable) -> None:
        if item not in self._parent:
            self._parent[item] = item
            self._rank[item] = 0
            self._parity[item] = 0

    def find(self, item: Hashable) -> tuple[Hashable, int]:
        self._ensure(item)
        parent = self._parent[item]
        if parent == item:
            return item, 0
        root, parent_parity = self.find(parent)
        item_parity = self._parity[item] ^ parent_parity
        self._parent[item] = root
        self._parity[item] = item_parity
        return root, item_parity

    def add_relation(self, first: Hashable, second: Hashable, parity: int) -> str:
        first_root, first_parity = self.find(first)
        second_root, second_parity = self.find(second)
        expected = parity & 1

        if first_root == second_root:
            actual = first_parity ^ second_parity
            return "REDUNDANT" if actual == expected else "CONFLICT"

        first_rank = self._rank[first_root]
        second_rank = self._rank[second_root]
        relation_to_parent = first_parity ^ second_parity ^ expected

        if first_rank < second_rank:
            self._parent[first_root] = second_root
            self._parity[first_root] = relation_to_parent
        elif first_rank > second_rank:
            self._parent[second_root] = first_root
            self._parity[second_root] = relation_to_parent
        else:
            self._parent[first_root] = second_root
            self._parity[first_root] = relation_to_parent
            self._rank[second_root] += 1
        return "ADDED"


class _DisjointSet:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        parent = self._parent.setdefault(item, item)
        if parent != item:
            self._parent[item] = self.find(parent)
        return self._parent[item]

    def add_relation(self, first: str, second: str) -> str:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root == second_root:
            return "REDUNDANT"
        if first_root <= second_root:
            self._parent[second_root] = first_root
        else:
            self._parent[first_root] = second_root
        return "ADDED"


class ConstraintSystemAnalyzer:
    """Diagnose direct global inconsistency without moving geometry.

    Ring 9 intentionally does not claim full CAD solver / degrees-of-freedom analysis.
    It proves only graph-level contradictions and safe transitive redundancies.
    """

    _WORLD_AXIS = ("MREA", "WORLD_AXIS")
    _ORIENTATION_KINDS = {"HORIZONTAL", "VERTICAL", "PARALLEL", "PERPENDICULAR"}
    _EQUIVALENCE_KINDS = {"EQUAL", "CONCENTRIC"}

    def analyze(self, resolution: ConstraintResolution) -> ConstraintSystemAnalysis:
        orientation = _ParityDisjointSet()
        equivalence = {kind: _DisjointSet() for kind in self._EQUIVALENCE_KINDS}

        accepted: list[ResolvedConstraint] = []
        issues = list(resolution.issues)
        redundant: list[str] = []
        rejected: list[str] = []

        for constraint in sorted(resolution.constraints, key=self._priority_key):
            outcome = self._classify(constraint, orientation, equivalence)
            if outcome == "ADDED" or outcome == "NOT_APPLICABLE":
                accepted.append(constraint)
                continue
            if outcome == "REDUNDANT":
                redundant.append(constraint.constraint_id)
                continue

            rejected.append(constraint.constraint_id)
            issues.append(
                ConstraintIssue(
                    issue_id=f"U-SYSTEM-{constraint.constraint_id}",
                    code="OVERCONSTRAINED_ORIENTATION_CONFLICT",
                    message=(
                        f"Constraint {constraint.constraint_id} contradicts stronger or "
                        "deterministically prior accepted orientation relations; it was not published."
                    ),
                    entity_ids=constraint.entity_ids,
                )
            )

        return ConstraintSystemAnalysis(
            resolution=ConstraintResolution(
                constraints=tuple(sorted(accepted, key=lambda item: item.constraint_id)),
                issues=tuple(sorted(issues, key=lambda item: item.issue_id)),
            ),
            redundant_constraint_ids=tuple(sorted(redundant)),
            rejected_constraint_ids=tuple(sorted(rejected)),
        )

    @staticmethod
    def _priority_key(constraint: ResolvedConstraint) -> tuple[float, int, str]:
        status_rank = 0 if constraint.status == "DETECTED" else 1
        return (-constraint.confidence, status_rank, constraint.constraint_id)

    def _classify(
        self,
        constraint: ResolvedConstraint,
        orientation: _ParityDisjointSet,
        equivalence: dict[str, _DisjointSet],
    ) -> str:
        if constraint.kind in self._ORIENTATION_KINDS:
            relation = self._orientation_relation(constraint)
            if relation is None:
                return "NOT_APPLICABLE"
            first, second, parity = relation
            return orientation.add_relation(first, second, parity)

        if constraint.kind in self._EQUIVALENCE_KINDS and len(constraint.entity_ids) == 2:
            first, second = constraint.entity_ids
            return equivalence[constraint.kind].add_relation(first, second)

        return "NOT_APPLICABLE"

    def _orientation_relation(
        self,
        constraint: ResolvedConstraint,
    ) -> tuple[Hashable, Hashable, int] | None:
        if constraint.kind in {"HORIZONTAL", "VERTICAL"}:
            if len(constraint.entity_ids) != 1:
                return None
            entity = ("ENTITY", constraint.entity_ids[0])
            parity = 0 if constraint.kind == "HORIZONTAL" else 1
            return entity, self._WORLD_AXIS, parity

        if constraint.kind in {"PARALLEL", "PERPENDICULAR"}:
            if len(constraint.entity_ids) != 2:
                return None
            first = ("ENTITY", constraint.entity_ids[0])
            second = ("ENTITY", constraint.entity_ids[1])
            parity = 0 if constraint.kind == "PARALLEL" else 1
            return first, second, parity

        return None
