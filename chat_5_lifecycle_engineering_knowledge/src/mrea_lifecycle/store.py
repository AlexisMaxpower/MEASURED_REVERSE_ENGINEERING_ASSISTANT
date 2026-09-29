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
    Revision,
    TestRecord,
)


class LifecycleInvariantError(ValueError):
    pass


@dataclass
class InMemoryLifecycleStore:
    """Phase-1 storage used to validate lifecycle invariants before persistence is added."""

    revisions: Dict[str, Revision] = field(default_factory=dict)
    manufacturing_records: Dict[str, ManufacturingRecord] = field(default_factory=dict)
    installations: Dict[str, Installation] = field(default_factory=dict)
    tests: Dict[str, TestRecord] = field(default_factory=dict)
    failures: Dict[str, FailureRecord] = field(default_factory=dict)
    events: List[LifecycleEvent] = field(default_factory=list)
    _sequence: int = 0

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

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
