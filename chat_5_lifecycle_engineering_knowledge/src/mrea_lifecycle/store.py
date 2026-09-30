from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .models import (
    FailureRecord,
    Installation,
    LifecycleEvent,
    LifecycleEventType,
    ManufacturingRecord,
    PhysicalLifecycleEvent,
    PhysicalLifecycleEventType,
    PhysicalPartInstance,
    PhysicalTestOutcome,
    Revision,
    TestRecord,
)


class LifecycleInvariantError(ValueError):
    pass


@dataclass
class InMemoryLifecycleStore:
    revisions: Dict[str, Revision] = field(default_factory=dict)
    manufacturing_records: Dict[str, ManufacturingRecord] = field(default_factory=dict)
    installations: Dict[str, Installation] = field(default_factory=dict)
    tests: Dict[str, TestRecord] = field(default_factory=dict)
    failures: Dict[str, FailureRecord] = field(default_factory=dict)
    events: List[LifecycleEvent] = field(default_factory=list)

    physical_instances: Dict[str, PhysicalPartInstance] = field(default_factory=dict)
    physical_events: List[PhysicalLifecycleEvent] = field(default_factory=list)

    _sequence: int = 0
    _physical_sequence: int = 0

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def next_physical_sequence(self) -> int:
        self._physical_sequence += 1
        return self._physical_sequence

    def append_event(
        self,
        *,
        event_id: str,
        event_type: LifecycleEventType,
        occurred_at: datetime,
        revision_id: str,
        manufacturing_id: Optional[str] = None,
        installation_id: Optional[str] = None,
        test_id: Optional[str] = None,
        failure_id: Optional[str] = None,
    ) -> LifecycleEvent:
        if any(event.event_id == event_id for event in self.events):
            raise LifecycleInvariantError(f"duplicate event_id: {event_id}")

        event = LifecycleEvent(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            sequence=self.next_sequence(),
            revision_id=revision_id,
            manufacturing_id=manufacturing_id,
            installation_id=installation_id,
            test_id=test_id,
            failure_id=failure_id,
        )
        self.events.append(event)
        return event

    def append_physical_event(
        self,
        *,
        event_id: str,
        event_type: PhysicalLifecycleEventType,
        occurred_at: datetime,
        instance_id: str,
        revision_id: str,
        manufacturing_id: str,
        installation_id: Optional[str] = None,
        test_id: Optional[str] = None,
        failure_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        position: Optional[str] = None,
        test_outcome: Optional[PhysicalTestOutcome] = None,
        replacement_instance_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PhysicalLifecycleEvent:
        if any(event.event_id == event_id for event in self.physical_events):
            raise LifecycleInvariantError(f"duplicate physical event_id: {event_id}")

        event = PhysicalLifecycleEvent(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            sequence=self.next_physical_sequence(),
            instance_id=instance_id,
            revision_id=revision_id,
            manufacturing_id=manufacturing_id,
            installation_id=installation_id,
            test_id=test_id,
            failure_id=failure_id,
            equipment_id=equipment_id,
            position=position,
            test_outcome=test_outcome,
            replacement_instance_id=replacement_instance_id,
            notes=notes,
        )
        self.physical_events.append(event)
        return event
