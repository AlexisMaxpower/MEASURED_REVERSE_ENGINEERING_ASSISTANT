from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional

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
    _transaction_depth: int = field(default=0, init=False, repr=False)
    _transaction_failed: bool = field(default=False, init=False, repr=False)
    _transaction_snapshot: Optional[dict[str, object]] = field(
        default=None, init=False, repr=False
    )

    @property
    def transaction_depth(self) -> int:
        return self._transaction_depth

    def _snapshot_state(self) -> dict[str, object]:
        return {
            "revisions": deepcopy(self.revisions),
            "manufacturing_records": deepcopy(self.manufacturing_records),
            "installations": deepcopy(self.installations),
            "tests": deepcopy(self.tests),
            "failures": deepcopy(self.failures),
            "events": deepcopy(self.events),
            "physical_instances": deepcopy(self.physical_instances),
            "physical_events": deepcopy(self.physical_events),
            "_sequence": self._sequence,
            "_physical_sequence": self._physical_sequence,
        }

    def _restore_state(self, snapshot: dict[str, object]) -> None:
        self.revisions = snapshot["revisions"]  # type: ignore[assignment]
        self.manufacturing_records = snapshot["manufacturing_records"]  # type: ignore[assignment]
        self.installations = snapshot["installations"]  # type: ignore[assignment]
        self.tests = snapshot["tests"]  # type: ignore[assignment]
        self.failures = snapshot["failures"]  # type: ignore[assignment]
        self.events = snapshot["events"]  # type: ignore[assignment]
        self.physical_instances = snapshot["physical_instances"]  # type: ignore[assignment]
        self.physical_events = snapshot["physical_events"]  # type: ignore[assignment]
        self._sequence = int(snapshot["_sequence"])
        self._physical_sequence = int(snapshot["_physical_sequence"])

    def _begin_outer_transaction(self) -> None:
        """Hook for durable repositories."""

    def _commit_outer_transaction(self) -> None:
        """Hook for durable repositories."""

    def _rollback_outer_transaction(self) -> None:
        """Hook for durable repositories."""

    @contextmanager
    def transaction(self) -> Iterator[InMemoryLifecycleStore]:
        """Atomic nested unit of work for lifecycle mutations.

        Only the outermost transaction snapshots/commits storage. Any nested failure
        marks the whole unit of work failed even if an inner exception is caught.
        """

        outermost = self._transaction_depth == 0
        if outermost:
            self._transaction_snapshot = self._snapshot_state()
            self._transaction_failed = False
            try:
                self._begin_outer_transaction()
            except Exception:
                self._transaction_snapshot = None
                raise

        self._transaction_depth += 1
        try:
            yield self
        except Exception:
            self._transaction_failed = True
            self._transaction_depth -= 1
            if outermost:
                snapshot = self._transaction_snapshot
                if snapshot is not None:
                    self._restore_state(snapshot)
                try:
                    self._rollback_outer_transaction()
                finally:
                    self._transaction_snapshot = None
                    self._transaction_failed = False
            raise
        else:
            self._transaction_depth -= 1
            if not outermost:
                return

            snapshot = self._transaction_snapshot
            if self._transaction_failed:
                if snapshot is not None:
                    self._restore_state(snapshot)
                try:
                    self._rollback_outer_transaction()
                finally:
                    self._transaction_snapshot = None
                    self._transaction_failed = False
                raise LifecycleInvariantError(
                    "nested lifecycle transaction failed and was rolled back"
                )

            try:
                self._commit_outer_transaction()
            except Exception:
                if snapshot is not None:
                    self._restore_state(snapshot)
                try:
                    self._rollback_outer_transaction()
                finally:
                    self._transaction_snapshot = None
                    self._transaction_failed = False
                raise
            else:
                self._transaction_snapshot = None
                self._transaction_failed = False

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
