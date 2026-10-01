from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .engineering_knowledge import LifecycleKnowledgeIntegrityError
from .revision_comparison import (
    RevisionComparisonDetailsResult,
    RevisionComparisonSnapshot,
)


@dataclass(frozen=True, slots=True)
class RevisionChangeSource:
    """Exact Chat-5 records/artifacts supporting one side of a factual delta."""

    revision_id: str
    record_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RevisionChangeFact:
    """One deterministic left-to-right difference with explicit evidence links."""

    category: str
    field: str
    left_value: object
    right_value: object
    left_source: RevisionChangeSource
    right_source: RevisionChangeSource


@dataclass(frozen=True, slots=True)
class RevisionChangeExplanation:
    """Structured factual explanation of how two committed revisions differ.

    The explanation is deliberately non-semantic: it reports only differences
    already present in RevisionComparisonDetailsResult and exact record/artifact
    identifiers supporting those differences. It never ranks revisions, recommends
    one, infers causality, or derives geometry.
    """

    part_id: str
    left_revision_id: str
    right_revision_id: str
    changed_categories: tuple[str, ...]
    facts: tuple[RevisionChangeFact, ...]


class RevisionComparisonKnowledge(Protocol):
    def compare_revision_details(
        self,
        left_revision_id: str,
        right_revision_id: str,
    ) -> RevisionComparisonDetailsResult: ...


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _manufacturing_source(snapshot: RevisionComparisonSnapshot) -> RevisionChangeSource:
    return RevisionChangeSource(
        revision_id=snapshot.revision_id,
        record_ids=tuple(fact.manufacturing_id for fact in snapshot.manufacturing),
    )


def _test_source(snapshot: RevisionComparisonSnapshot) -> RevisionChangeSource:
    return RevisionChangeSource(
        revision_id=snapshot.revision_id,
        record_ids=tuple(fact.test_id for fact in snapshot.tests),
        artifact_ids=_ordered_unique(
            tuple(
                artifact_id
                for fact in snapshot.tests
                for artifact_id in fact.artifact_ids
            )
        ),
    )


def _failure_source(snapshot: RevisionComparisonSnapshot) -> RevisionChangeSource:
    return RevisionChangeSource(
        revision_id=snapshot.revision_id,
        record_ids=tuple(fact.failure_id for fact in snapshot.failures),
        artifact_ids=_ordered_unique(
            tuple(
                artifact_id
                for fact in snapshot.failures
                for artifact_id in fact.evidence_artifact_ids
            )
        ),
    )


def _revision_source(snapshot: RevisionComparisonSnapshot) -> RevisionChangeSource:
    return RevisionChangeSource(revision_id=snapshot.revision_id)


def _append_if_changed(
    facts: list[RevisionChangeFact],
    *,
    category: str,
    field: str,
    left_value: object,
    right_value: object,
    left_source: RevisionChangeSource,
    right_source: RevisionChangeSource,
) -> None:
    if left_value == right_value:
        return
    facts.append(
        RevisionChangeFact(
            category=category,
            field=field,
            left_value=left_value,
            right_value=right_value,
            left_source=left_source,
            right_source=right_source,
        )
    )


def build_revision_change_explanation(
    details: RevisionComparisonDetailsResult,
) -> RevisionChangeExplanation:
    """Convert durable comparison details into deterministic factual deltas."""

    left = details.left
    right = details.right
    if left.part_id != right.part_id:
        raise LifecycleKnowledgeIntegrityError(
            "revision comparison details contain different part identifiers"
        )

    facts: list[RevisionChangeFact] = []
    left_revision = _revision_source(left)
    right_revision = _revision_source(right)

    for field in (
        "parent_revision_id",
        "origin",
        "notes",
        "source_cad_artifact_id",
    ):
        _append_if_changed(
            facts,
            category="revision_metadata",
            field=field,
            left_value=getattr(left, field),
            right_value=getattr(right, field),
            left_source=left_revision,
            right_source=right_revision,
        )

    for field in (
        "verification_status",
        "runtime_status",
        "runtime_evidence_schema_version",
        "runtime_real_host_executed",
    ):
        _append_if_changed(
            facts,
            category="cad_truth",
            field=field,
            left_value=getattr(left, field),
            right_value=getattr(right, field),
            left_source=left_revision,
            right_source=right_revision,
        )

    left_manufacturing = _manufacturing_source(left)
    right_manufacturing = _manufacturing_source(right)
    _append_if_changed(
        facts,
        category="materials",
        field="materials",
        left_value=left.materials,
        right_value=right.materials,
        left_source=left_manufacturing,
        right_source=right_manufacturing,
    )
    _append_if_changed(
        facts,
        category="manufacturing_methods",
        field="manufacturing_methods",
        left_value=left.manufacturing_methods,
        right_value=right.manufacturing_methods,
        left_source=left_manufacturing,
        right_source=right_manufacturing,
    )
    _append_if_changed(
        facts,
        category="manufacturing_records",
        field="manufacturing",
        left_value=left.manufacturing,
        right_value=right.manufacturing,
        left_source=left_manufacturing,
        right_source=right_manufacturing,
    )

    _append_if_changed(
        facts,
        category="tests",
        field="tests",
        left_value=left.tests,
        right_value=right.tests,
        left_source=_test_source(left),
        right_source=_test_source(right),
    )
    _append_if_changed(
        facts,
        category="failures",
        field="failures",
        left_value=left.failures,
        right_value=right.failures,
        left_source=_failure_source(left),
        right_source=_failure_source(right),
    )
    _append_if_changed(
        facts,
        category="lifecycle_state",
        field="state",
        left_value=left.state,
        right_value=right.state,
        left_source=left_revision,
        right_source=right_revision,
    )

    fact_categories = tuple(dict.fromkeys(fact.category for fact in facts))
    if fact_categories != details.changed_categories:
        raise LifecycleKnowledgeIntegrityError(
            "revision explanation categories diverge from durable comparison"
        )

    return RevisionChangeExplanation(
        part_id=left.part_id,
        left_revision_id=left.revision_id,
        right_revision_id=right.revision_id,
        changed_categories=details.changed_categories,
        facts=tuple(facts),
    )


def explain_revision_changes(
    knowledge: RevisionComparisonKnowledge,
    left_revision_id: str,
    right_revision_id: str,
) -> RevisionChangeExplanation:
    """Read committed facts and return a deterministic evidence-backed explanation."""

    return build_revision_change_explanation(
        knowledge.compare_revision_details(left_revision_id, right_revision_id)
    )
