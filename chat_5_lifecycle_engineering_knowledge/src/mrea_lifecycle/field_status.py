from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .engineering_knowledge import LifecycleKnowledgeIntegrityError
from .models import PhysicalLifecycleEventType, PhysicalPartState
from .relational import PhysicalEventQueryResult


_STATE_BY_EVENT = {
    PhysicalLifecycleEventType.MANUFACTURED: PhysicalPartState.MANUFACTURED,
    PhysicalLifecycleEventType.INSTALLED: PhysicalPartState.INSTALLED,
    PhysicalLifecycleEventType.TESTED: PhysicalPartState.TESTED,
    PhysicalLifecycleEventType.ACTIVATED: PhysicalPartState.ACTIVE,
    PhysicalLifecycleEventType.FAILED: PhysicalPartState.FAILED,
    PhysicalLifecycleEventType.REMOVED: PhysicalPartState.REMOVED,
    PhysicalLifecycleEventType.SUPERSEDED: PhysicalPartState.SUPERSEDED,
}


@dataclass(frozen=True, slots=True)
class PhysicalFieldStatus:
    """Current deterministic field state of one committed physical instance.

    The status is a projection of the instance's durable physical timeline. Location
    and linkage fields are copied from the latest persisted physical event; they are
    evidence context, not an independent occupancy or causality claim.
    """

    instance_id: str
    revision_id: str
    manufacturing_id: str
    state: PhysicalPartState
    state_changed_at: datetime
    source_event_id: str
    source_event_sequence: int
    installation_id: str | None
    test_id: str | None
    failure_id: str | None
    equipment_id: str | None
    position: str | None
    test_outcome: str | None
    replacement_instance_id: str | None
    notes: str | None


class PhysicalTimelineQuery(Protocol):
    def physical_timeline(
        self,
        instance_id: str,
    ) -> tuple[PhysicalEventQueryResult, ...]: ...


def build_physical_field_status(
    timeline: tuple[PhysicalEventQueryResult, ...],
) -> PhysicalFieldStatus:
    """Build one fail-closed current-state projection from an ordered durable timeline."""

    if not timeline:
        raise ValueError("physical instance does not exist or has no lifecycle events")

    expected_instance_id = timeline[0].instance_id
    expected_revision_id = timeline[0].revision_id
    expected_manufacturing_id = timeline[0].manufacturing_id
    previous_sequence: int | None = None
    previous_time: datetime | None = None

    for event in timeline:
        if event.instance_id != expected_instance_id:
            raise LifecycleKnowledgeIntegrityError(
                "physical field-status timeline contains multiple instance identifiers"
            )
        if event.revision_id != expected_revision_id:
            raise LifecycleKnowledgeIntegrityError(
                "physical field-status timeline changes revision identity"
            )
        if event.manufacturing_id != expected_manufacturing_id:
            raise LifecycleKnowledgeIntegrityError(
                "physical field-status timeline changes manufacturing identity"
            )
        if previous_sequence is not None and event.sequence <= previous_sequence:
            raise LifecycleKnowledgeIntegrityError(
                "physical field-status timeline sequence is not strictly increasing"
            )
        if previous_time is not None and event.occurred_at < previous_time:
            raise LifecycleKnowledgeIntegrityError(
                "physical field-status timeline moves backward in time"
            )
        previous_sequence = event.sequence
        previous_time = event.occurred_at

    latest = timeline[-1]
    try:
        event_type = PhysicalLifecycleEventType(latest.event_type)
    except ValueError as exc:
        raise LifecycleKnowledgeIntegrityError(
            f"unsupported physical lifecycle event type: {latest.event_type}"
        ) from exc

    return PhysicalFieldStatus(
        instance_id=latest.instance_id,
        revision_id=latest.revision_id,
        manufacturing_id=latest.manufacturing_id,
        state=_STATE_BY_EVENT[event_type],
        state_changed_at=latest.occurred_at,
        source_event_id=latest.event_id,
        source_event_sequence=latest.sequence,
        installation_id=latest.installation_id,
        test_id=latest.test_id,
        failure_id=latest.failure_id,
        equipment_id=latest.equipment_id,
        position=latest.position,
        test_outcome=latest.test_outcome,
        replacement_instance_id=latest.replacement_instance_id,
        notes=latest.notes,
    )


def get_physical_field_status(
    queries: PhysicalTimelineQuery,
    instance_id: str,
) -> PhysicalFieldStatus:
    """Read one committed timeline and return its deterministic current field status."""

    if not isinstance(instance_id, str) or not instance_id.strip():
        raise ValueError("instance_id must be a non-empty string")
    return build_physical_field_status(queries.physical_timeline(instance_id))
