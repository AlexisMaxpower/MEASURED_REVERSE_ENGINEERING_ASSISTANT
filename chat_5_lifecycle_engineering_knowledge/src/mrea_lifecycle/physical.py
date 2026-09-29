from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from .models import (
    FailureRecord,
    Installation,
    PhysicalLifecycleEvent,
    PhysicalLifecycleEventType,
    PhysicalPartInstance,
    PhysicalPartState,
    PhysicalTestOutcome,
    TestRecord,
)
from .services import FailureService, InstallationService, TestService
from .store import InMemoryLifecycleStore, LifecycleInvariantError


_STATE_BY_EVENT = {
    PhysicalLifecycleEventType.MANUFACTURED: PhysicalPartState.MANUFACTURED,
    PhysicalLifecycleEventType.INSTALLED: PhysicalPartState.INSTALLED,
    PhysicalLifecycleEventType.TESTED: PhysicalPartState.TESTED,
    PhysicalLifecycleEventType.ACTIVATED: PhysicalPartState.ACTIVE,
    PhysicalLifecycleEventType.FAILED: PhysicalPartState.FAILED,
    PhysicalLifecycleEventType.REMOVED: PhysicalPartState.REMOVED,
    PhysicalLifecycleEventType.SUPERSEDED: PhysicalPartState.SUPERSEDED,
}
_OCCUPYING_STATES = {
    PhysicalPartState.INSTALLED,
    PhysicalPartState.TESTED,
    PhysicalPartState.ACTIVE,
    PhysicalPartState.FAILED,
}


def _require_non_empty(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifecycleInvariantError(f"{field_name} must be a non-empty string")
    return value


def _require_aware(timestamp: datetime, *, field_name: str) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise LifecycleInvariantError(f"{field_name} must be timezone-aware")


class PhysicalPartTimeline:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def for_instance(self, instance_id: str) -> Tuple[PhysicalLifecycleEvent, ...]:
        if instance_id not in self.store.physical_instances:
            raise LifecycleInvariantError(f"unknown instance_id: {instance_id}")
        return tuple(
            sorted(
                (
                    event
                    for event in self.store.physical_events
                    if event.instance_id == instance_id
                ),
                key=lambda event: (event.occurred_at, event.sequence),
            )
        )


class PhysicalPartStateProjection:
    def __init__(
        self,
        store: InMemoryLifecycleStore,
        timeline: Optional[PhysicalPartTimeline] = None,
    ) -> None:
        self.store = store
        self.timeline = timeline or PhysicalPartTimeline(store)

    def for_instance(self, instance_id: str) -> PhysicalPartState:
        events = self.timeline.for_instance(instance_id)
        if not events:
            raise LifecycleInvariantError(
                f"physical instance has no lifecycle events: {instance_id}"
            )
        return _STATE_BY_EVENT[events[-1].event_type]


class PhysicalEquipmentRegistry:
    def __init__(
        self,
        store: InMemoryLifecycleStore,
        timeline: Optional[PhysicalPartTimeline] = None,
        states: Optional[PhysicalPartStateProjection] = None,
    ) -> None:
        self.store = store
        self.timeline = timeline or PhysicalPartTimeline(store)
        self.states = states or PhysicalPartStateProjection(store, self.timeline)

    def current_instance(
        self, *, equipment_id: str, position: str
    ) -> Optional[PhysicalPartInstance]:
        matches: list[PhysicalPartInstance] = []
        for instance in self.store.physical_instances.values():
            state = self.states.for_instance(instance.instance_id)
            if state not in _OCCUPYING_STATES:
                continue
            latest = self.timeline.for_instance(instance.instance_id)[-1]
            if latest.equipment_id == equipment_id and latest.position == position:
                matches.append(instance)

        if len(matches) > 1:
            raise LifecycleInvariantError(
                f"multiple active physical instances occupy {equipment_id}/{position}"
            )
        return matches[0] if matches else None


class PhysicalPartLifecycleService:
    """Fail-closed state machine for the life of one real manufactured item."""

    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store
        self.timeline = PhysicalPartTimeline(store)
        self.states = PhysicalPartStateProjection(store, self.timeline)
        self.registry = PhysicalEquipmentRegistry(store, self.timeline, self.states)
        self.installations = InstallationService(store)
        self.tests = TestService(store)
        self.failures = FailureService(store)

    def _instance(self, instance_id: str) -> PhysicalPartInstance:
        instance = self.store.physical_instances.get(instance_id)
        if instance is None:
            raise LifecycleInvariantError(f"unknown instance_id: {instance_id}")
        return instance

    def _ensure_physical_event_id_available(self, event_id: str) -> None:
        _require_non_empty(event_id, field_name="physical_event_id")
        if any(event.event_id == event_id for event in self.store.physical_events):
            raise LifecycleInvariantError(f"duplicate physical event_id: {event_id}")

    def _ensure_canonical_event_id_available(self, event_id: str) -> None:
        _require_non_empty(event_id, field_name="lifecycle_event_id")
        if any(event.event_id == event_id for event in self.store.events):
            raise LifecycleInvariantError(f"duplicate event_id: {event_id}")

    def _latest(self, instance_id: str) -> PhysicalLifecycleEvent:
        events = self.timeline.for_instance(instance_id)
        if not events:
            raise LifecycleInvariantError(
                f"physical instance has no lifecycle events: {instance_id}"
            )
        return events[-1]

    def _ensure_monotonic(self, instance_id: str, occurred_at: datetime) -> None:
        _require_aware(occurred_at, field_name="occurred_at")
        latest = self._latest(instance_id)
        if occurred_at < latest.occurred_at:
            raise LifecycleInvariantError(
                "physical lifecycle event cannot move backward in time"
            )

    def _location(
        self, instance_id: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        for event in reversed(self.timeline.for_instance(instance_id)):
            if event.equipment_id is not None and event.position is not None:
                return event.equipment_id, event.position, event.installation_id
        return None, None, None

    def register_manufactured(
        self,
        *,
        instance_id: str,
        manufacturing_id: str,
        physical_event_id: str,
    ) -> PhysicalPartInstance:
        _require_non_empty(instance_id, field_name="instance_id")
        _require_non_empty(manufacturing_id, field_name="manufacturing_id")
        self._ensure_physical_event_id_available(physical_event_id)

        if instance_id in self.store.physical_instances:
            raise LifecycleInvariantError(f"duplicate instance_id: {instance_id}")

        manufacturing = self.store.manufacturing_records.get(manufacturing_id)
        if manufacturing is None:
            raise LifecycleInvariantError(
                f"unknown manufacturing_id: {manufacturing_id}"
            )
        revision = self.store.revisions.get(manufacturing.revision_id)
        if revision is None:
            raise LifecycleInvariantError(
                f"unknown revision_id: {manufacturing.revision_id}"
            )
        _require_aware(manufacturing.manufactured_at, field_name="manufactured_at")

        instance = PhysicalPartInstance(
            instance_id=instance_id,
            part_id=revision.part_id,
            revision_id=revision.revision_id,
            manufacturing_id=manufacturing.manufacturing_id,
            material=manufacturing.material,
            method=manufacturing.method,
            manufactured_at=manufacturing.manufactured_at,
            batch=manufacturing.batch,
            machine=manufacturing.machine,
            print_profile=manufacturing.print_profile,
        )
        self.store.physical_instances[instance_id] = instance
        self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.MANUFACTURED,
            occurred_at=manufacturing.manufactured_at,
            instance_id=instance.instance_id,
            revision_id=instance.revision_id,
            manufacturing_id=instance.manufacturing_id,
        )
        return instance

    def install(
        self,
        installation: Installation,
        *,
        lifecycle_event_id: str,
        physical_event_id: str,
    ) -> Installation:
        if installation.instance_id is None:
            raise LifecycleInvariantError("physical installation requires instance_id")
        instance = self._instance(installation.instance_id)
        if self.states.for_instance(instance.instance_id) is not PhysicalPartState.MANUFACTURED:
            raise LifecycleInvariantError(
                "physical instance must be MANUFACTURED before installation"
            )
        if installation.revision_id != instance.revision_id:
            raise LifecycleInvariantError(
                "installation revision does not match physical instance revision"
            )
        if installation.manufacturing_id != instance.manufacturing_id:
            raise LifecycleInvariantError(
                "installation manufacturing does not match physical instance"
            )
        _require_non_empty(installation.equipment_id, field_name="equipment_id")
        _require_non_empty(installation.position, field_name="position")
        self._ensure_monotonic(instance.instance_id, installation.installed_at)
        self._ensure_canonical_event_id_available(lifecycle_event_id)
        self._ensure_physical_event_id_available(physical_event_id)

        occupant = self.registry.current_instance(
            equipment_id=installation.equipment_id,
            position=installation.position,
        )
        if occupant is not None and occupant.instance_id != instance.instance_id:
            raise LifecycleInvariantError(
                f"equipment position already occupied by instance {occupant.instance_id}"
            )

        stored = self.installations.install(installation, event_id=lifecycle_event_id)
        self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.INSTALLED,
            occurred_at=installation.installed_at,
            instance_id=instance.instance_id,
            revision_id=instance.revision_id,
            manufacturing_id=instance.manufacturing_id,
            installation_id=installation.installation_id,
            equipment_id=installation.equipment_id,
            position=installation.position,
        )
        return stored

    def test(
        self,
        record: TestRecord,
        *,
        outcome: PhysicalTestOutcome,
        lifecycle_event_id: str,
        physical_event_id: str,
    ) -> TestRecord:
        if record.instance_id is None:
            raise LifecycleInvariantError("physical test requires instance_id")
        instance = self._instance(record.instance_id)
        state = self.states.for_instance(instance.instance_id)
        if state not in {PhysicalPartState.INSTALLED, PhysicalPartState.TESTED}:
            raise LifecycleInvariantError(
                "physical instance must be INSTALLED or TESTED before testing"
            )
        if record.revision_id != instance.revision_id:
            raise LifecycleInvariantError(
                "test revision does not match physical instance revision"
            )
        if record.manufacturing_id != instance.manufacturing_id:
            raise LifecycleInvariantError(
                "test manufacturing does not match physical instance"
            )
        equipment_id, position, installation_id = self._location(instance.instance_id)
        if installation_id is None or record.installation_id != installation_id:
            raise LifecycleInvariantError(
                "test installation does not match physical instance installation"
            )
        try:
            explicit_outcome = PhysicalTestOutcome(outcome)
        except (TypeError, ValueError) as exc:
            raise LifecycleInvariantError(
                "physical test outcome must be PASSED or FAILED"
            ) from exc

        self._ensure_monotonic(instance.instance_id, record.tested_at)
        self._ensure_canonical_event_id_available(lifecycle_event_id)
        self._ensure_physical_event_id_available(physical_event_id)

        stored = self.tests.record(record, event_id=lifecycle_event_id)
        self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.TESTED,
            occurred_at=record.tested_at,
            instance_id=instance.instance_id,
            revision_id=instance.revision_id,
            manufacturing_id=instance.manufacturing_id,
            installation_id=record.installation_id,
            test_id=record.test_id,
            equipment_id=equipment_id,
            position=position,
            test_outcome=explicit_outcome,
        )
        return stored

    def activate(
        self,
        *,
        instance_id: str,
        activated_at: datetime,
        physical_event_id: str,
        notes: Optional[str] = None,
    ) -> PhysicalLifecycleEvent:
        instance = self._instance(instance_id)
        if self.states.for_instance(instance_id) is not PhysicalPartState.TESTED:
            raise LifecycleInvariantError(
                "physical instance must be TESTED before activation"
            )
        latest = self._latest(instance_id)
        if (
            latest.event_type is not PhysicalLifecycleEventType.TESTED
            or latest.test_outcome is not PhysicalTestOutcome.PASSED
        ):
            raise LifecycleInvariantError(
                "latest physical test must be PASSED before activation"
            )
        self._ensure_monotonic(instance_id, activated_at)
        self._ensure_physical_event_id_available(physical_event_id)
        equipment_id, position, installation_id = self._location(instance_id)
        return self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.ACTIVATED,
            occurred_at=activated_at,
            instance_id=instance.instance_id,
            revision_id=instance.revision_id,
            manufacturing_id=instance.manufacturing_id,
            installation_id=installation_id,
            test_id=latest.test_id,
            equipment_id=equipment_id,
            position=position,
            notes=notes,
        )

    def fail(
        self,
        record: FailureRecord,
        *,
        lifecycle_event_id: str,
        physical_event_id: str,
    ) -> FailureRecord:
        if record.instance_id is None:
            raise LifecycleInvariantError("physical failure requires instance_id")
        instance = self._instance(record.instance_id)
        state = self.states.for_instance(instance.instance_id)
        if state not in {
            PhysicalPartState.INSTALLED,
            PhysicalPartState.TESTED,
            PhysicalPartState.ACTIVE,
        }:
            raise LifecycleInvariantError(
                "physical instance must be installed/in-service before failure"
            )
        if record.revision_id != instance.revision_id:
            raise LifecycleInvariantError(
                "failure revision does not match physical instance revision"
            )
        if record.manufacturing_id != instance.manufacturing_id:
            raise LifecycleInvariantError(
                "failure manufacturing does not match physical instance"
            )
        equipment_id, position, installation_id = self._location(instance.instance_id)
        if installation_id is None or record.installation_id != installation_id:
            raise LifecycleInvariantError(
                "failure installation does not match physical instance installation"
            )

        self._ensure_monotonic(instance.instance_id, record.failed_at)
        self._ensure_canonical_event_id_available(lifecycle_event_id)
        self._ensure_physical_event_id_available(physical_event_id)

        stored = self.failures.record(record, event_id=lifecycle_event_id)
        self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.FAILED,
            occurred_at=record.failed_at,
            instance_id=instance.instance_id,
            revision_id=instance.revision_id,
            manufacturing_id=instance.manufacturing_id,
            installation_id=record.installation_id,
            failure_id=record.failure_id,
            equipment_id=equipment_id,
            position=position,
        )
        return stored

    def remove(
        self,
        *,
        instance_id: str,
        removed_at: datetime,
        physical_event_id: str,
        reason: str,
    ) -> PhysicalLifecycleEvent:
        instance = self._instance(instance_id)
        state = self.states.for_instance(instance_id)
        if state not in {
            PhysicalPartState.INSTALLED,
            PhysicalPartState.TESTED,
            PhysicalPartState.ACTIVE,
            PhysicalPartState.FAILED,
        }:
            raise LifecycleInvariantError(
                f"cannot remove physical instance from state {state.value}"
            )
        _require_non_empty(reason, field_name="removal reason")
        self._ensure_monotonic(instance_id, removed_at)
        self._ensure_physical_event_id_available(physical_event_id)
        equipment_id, position, installation_id = self._location(instance_id)
        return self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.REMOVED,
            occurred_at=removed_at,
            instance_id=instance.instance_id,
            revision_id=instance.revision_id,
            manufacturing_id=instance.manufacturing_id,
            installation_id=installation_id,
            equipment_id=equipment_id,
            position=position,
            notes=reason,
        )

    def supersede(
        self,
        *,
        instance_id: str,
        replacement_instance_id: str,
        superseded_at: datetime,
        physical_event_id: str,
        notes: Optional[str] = None,
    ) -> PhysicalLifecycleEvent:
        old = self._instance(instance_id)
        replacement = self._instance(replacement_instance_id)
        if old.instance_id == replacement.instance_id:
            raise LifecycleInvariantError(
                "replacement instance must differ from superseded instance"
            )
        if self.states.for_instance(old.instance_id) is not PhysicalPartState.REMOVED:
            raise LifecycleInvariantError(
                "physical instance must be REMOVED before superseding"
            )
        replacement_state = self.states.for_instance(replacement.instance_id)
        if replacement_state not in {
            PhysicalPartState.INSTALLED,
            PhysicalPartState.TESTED,
            PhysicalPartState.ACTIVE,
        }:
            raise LifecycleInvariantError(
                "replacement instance must be installed or in service"
            )
        if old.part_id != replacement.part_id:
            raise LifecycleInvariantError(
                "replacement instance belongs to a different part"
            )

        old_equipment, old_position, old_installation = self._location(old.instance_id)
        new_equipment, new_position, _ = self._location(replacement.instance_id)
        if (
            old_equipment is None
            or old_position is None
            or (old_equipment, old_position) != (new_equipment, new_position)
        ):
            raise LifecycleInvariantError(
                "replacement instance must occupy the same equipment position"
            )

        self._ensure_monotonic(old.instance_id, superseded_at)
        _require_aware(superseded_at, field_name="superseded_at")
        if superseded_at < self._latest(replacement.instance_id).occurred_at:
            raise LifecycleInvariantError(
                "superseded_at cannot precede replacement lifecycle state"
            )
        self._ensure_physical_event_id_available(physical_event_id)
        return self.store.append_physical_event(
            event_id=physical_event_id,
            event_type=PhysicalLifecycleEventType.SUPERSEDED,
            occurred_at=superseded_at,
            instance_id=old.instance_id,
            revision_id=old.revision_id,
            manufacturing_id=old.manufacturing_id,
            installation_id=old_installation,
            equipment_id=old_equipment,
            position=old_position,
            replacement_instance_id=replacement.instance_id,
            notes=notes,
        )
