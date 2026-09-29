from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from .models import Installation, LifecycleEvent, LifecycleEventType, LifecycleState
from .store import InMemoryLifecycleStore, LifecycleInvariantError


class LifecycleTimeline:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def for_revision(self, revision_id: str) -> Tuple[LifecycleEvent, ...]:
        if revision_id not in self.store.revisions:
            raise LifecycleInvariantError(f"unknown revision_id: {revision_id}")
        return tuple(
            sorted(
                (event for event in self.store.events if event.revision_id == revision_id),
                key=lambda event: (event.occurred_at, event.sequence),
            )
        )

    def for_part(self, part_id: str) -> Tuple[LifecycleEvent, ...]:
        revision_ids = {
            revision.revision_id
            for revision in self.store.revisions.values()
            if revision.part_id == part_id
        }
        return tuple(
            sorted(
                (event for event in self.store.events if event.revision_id in revision_ids),
                key=lambda event: (event.occurred_at, event.sequence),
            )
        )


class EquipmentPartRegistry:
    """Derives the current mapping from installation history; old installations are retained."""

    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def current_installation(
        self, *, equipment_id: str, position: str
    ) -> Optional[Installation]:
        matching_events = []
        for event in self.store.events:
            if event.event_type is not LifecycleEventType.INSTALLED:
                continue
            if event.installation_id is None:
                continue
            installation = self.store.installations[event.installation_id]
            if (
                installation.equipment_id == equipment_id
                and installation.position == position
            ):
                matching_events.append((event, installation))

        if not matching_events:
            return None

        _, installation = max(
            matching_events,
            key=lambda pair: (pair[0].occurred_at, pair[0].sequence),
        )
        return installation


class LifecycleStateProjection:
    def __init__(
        self,
        store: InMemoryLifecycleStore,
        timeline: LifecycleTimeline,
        registry: EquipmentPartRegistry,
    ) -> None:
        self.store = store
        self.timeline = timeline
        self.registry = registry

    def for_revision(self, revision_id: str) -> LifecycleState:
        events = self.timeline.for_revision(revision_id)
        if not events:
            raise LifecycleInvariantError(
                f"revision has no lifecycle events: {revision_id}"
            )

        if any(event.event_type is LifecycleEventType.FAILED for event in events):
            latest_failure = max(
                (event for event in events if event.event_type is LifecycleEventType.FAILED),
                key=lambda event: (event.occurred_at, event.sequence),
            )
            latest_install = max(
                (event for event in events if event.event_type is LifecycleEventType.INSTALLED),
                key=lambda event: (event.occurred_at, event.sequence),
                default=None,
            )
            if latest_install is None or (
                latest_failure.occurred_at,
                latest_failure.sequence,
            ) > (latest_install.occurred_at, latest_install.sequence):
                return LifecycleState.FAILED

        latest = events[-1]
        if latest.event_type is LifecycleEventType.REVISION_CREATED:
            return LifecycleState.DRAFT
        if latest.event_type is LifecycleEventType.MANUFACTURED:
            return LifecycleState.MANUFACTURED
        if latest.event_type in {LifecycleEventType.INSTALLED, LifecycleEventType.TESTED}:
            return LifecycleState.ACTIVE
        if latest.event_type is LifecycleEventType.FAILED:
            return LifecycleState.FAILED

        raise LifecycleInvariantError(
            f"cannot project state from event type: {latest.event_type}"
        )


@dataclass(frozen=True, slots=True)
class RevisionComparisonResult:
    left_revision_id: str
    right_revision_id: str
    left_materials: Tuple[str, ...]
    right_materials: Tuple[str, ...]
    left_failure_count: int
    right_failure_count: int
    left_test_count: int
    right_test_count: int
    left_state: LifecycleState
    right_state: LifecycleState


class RevisionComparison:
    def __init__(
        self,
        store: InMemoryLifecycleStore,
        state_projection: LifecycleStateProjection,
    ) -> None:
        self.store = store
        self.state_projection = state_projection

    def compare(self, left_revision_id: str, right_revision_id: str) -> RevisionComparisonResult:
        left = self.store.revisions.get(left_revision_id)
        right = self.store.revisions.get(right_revision_id)
        if left is None or right is None:
            raise LifecycleInvariantError("both revisions must exist")
        if left.part_id != right.part_id:
            raise LifecycleInvariantError("cannot compare revisions from different parts")

        def materials(revision_id: str) -> Tuple[str, ...]:
            return tuple(
                sorted(
                    {
                        record.material
                        for record in self.store.manufacturing_records.values()
                        if record.revision_id == revision_id
                    }
                )
            )

        def count_for(records: Iterable[object], revision_id: str) -> int:
            return sum(
                1
                for record in records
                if getattr(record, "revision_id") == revision_id
            )

        return RevisionComparisonResult(
            left_revision_id=left_revision_id,
            right_revision_id=right_revision_id,
            left_materials=materials(left_revision_id),
            right_materials=materials(right_revision_id),
            left_failure_count=count_for(self.store.failures.values(), left_revision_id),
            right_failure_count=count_for(self.store.failures.values(), right_revision_id),
            left_test_count=count_for(self.store.tests.values(), left_revision_id),
            right_test_count=count_for(self.store.tests.values(), right_revision_id),
            left_state=self.state_projection.for_revision(left_revision_id),
            right_state=self.state_projection.for_revision(right_revision_id),
        )


class KnowledgeQueryService:
    """Deterministic structured queries only. No AI/semantic inference in phase 1."""

    def __init__(
        self,
        store: InMemoryLifecycleStore,
        registry: EquipmentPartRegistry,
    ) -> None:
        self.store = store
        self.registry = registry

    def failed_revision_ids(self, *, part_id: Optional[str] = None) -> Tuple[str, ...]:
        revision_ids = {
            failure.revision_id for failure in self.store.failures.values()
        }
        if part_id is not None:
            revision_ids = {
                revision_id
                for revision_id in revision_ids
                if self.store.revisions[revision_id].part_id == part_id
            }
        return tuple(sorted(revision_ids))

    def current_revision_for_equipment(
        self, *, equipment_id: str, position: str
    ) -> Optional[str]:
        installation = self.registry.current_installation(
            equipment_id=equipment_id,
            position=position,
        )
        return installation.revision_id if installation is not None else None
