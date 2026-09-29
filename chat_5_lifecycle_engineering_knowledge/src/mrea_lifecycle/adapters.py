from __future__ import annotations

from datetime import timezone
from typing import Iterable

from .models import LifecycleEvent, LifecycleEventType
from .store import LifecycleInvariantError


CANONICAL_LIFECYCLE_EVENT_SCHEMA_VERSION = "mrea.lifecycle-event.v1"
CANONICAL_LIFECYCLE_EVENT_TYPES = frozenset(
    event_type.value for event_type in LifecycleEventType
)
_REQUIRED_REFERENCE_BY_EVENT_TYPE = {
    LifecycleEventType.MANUFACTURED: "manufacturing_id",
    LifecycleEventType.INSTALLED: "installation_id",
    LifecycleEventType.TESTED: "test_id",
    LifecycleEventType.FAILED: "failure_id",
}


class CanonicalLifecycleEventAdapter:
    """Outbound boundary from Chat 5 internal events to LifecycleEvent v1."""

    @staticmethod
    def to_contract(event: LifecycleEvent) -> dict[str, object]:
        if not event.event_id:
            raise LifecycleInvariantError("canonical lifecycle event requires event_id")
        if not event.revision_id:
            raise LifecycleInvariantError("canonical lifecycle event requires revision_id")
        if event.sequence < 1:
            raise LifecycleInvariantError(
                "canonical lifecycle event sequence must be >= 1"
            )
        if event.event_type.value not in CANONICAL_LIFECYCLE_EVENT_TYPES:
            raise LifecycleInvariantError(
                f"unsupported canonical lifecycle event type: {event.event_type.value}"
            )
        if event.occurred_at.tzinfo is None or event.occurred_at.utcoffset() is None:
            raise LifecycleInvariantError(
                "canonical lifecycle event requires timezone-aware occurred_at"
            )

        required_reference = _REQUIRED_REFERENCE_BY_EVENT_TYPE.get(event.event_type)
        if required_reference is not None and getattr(event, required_reference) is None:
            raise LifecycleInvariantError(
                f"{event.event_type.value} requires {required_reference}"
            )

        occurred_at = (
            event.occurred_at.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return {
            "schema_version": CANONICAL_LIFECYCLE_EVENT_SCHEMA_VERSION,
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "occurred_at": occurred_at,
            "sequence": event.sequence,
            "revision_id": event.revision_id,
            "manufacturing_id": event.manufacturing_id,
            "installation_id": event.installation_id,
            "test_id": event.test_id,
            "failure_id": event.failure_id,
        }

    def export(
        self, events: Iterable[LifecycleEvent]
    ) -> tuple[dict[str, object], ...]:
        ordered = sorted(events, key=lambda event: event.sequence)
        seen_event_ids: set[str] = set()
        seen_sequences: set[int] = set()
        result: list[dict[str, object]] = []

        for event in ordered:
            if event.event_id in seen_event_ids:
                raise LifecycleInvariantError(
                    f"duplicate event_id during canonical export: {event.event_id}"
                )
            if event.sequence in seen_sequences:
                raise LifecycleInvariantError(
                    f"duplicate sequence during canonical export: {event.sequence}"
                )
            seen_event_ids.add(event.event_id)
            seen_sequences.add(event.sequence)
            result.append(self.to_contract(event))

        return tuple(result)
