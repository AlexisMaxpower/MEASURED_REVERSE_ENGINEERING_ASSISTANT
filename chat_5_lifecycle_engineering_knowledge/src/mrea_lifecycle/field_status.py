from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .engineering_knowledge import LifecycleKnowledgeIntegrityError
from .models import PhysicalLifecycleEventType, PhysicalPartState, PhysicalTestOutcome
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

_ALLOWED_NEXT_EVENTS = {
    PhysicalLifecycleEventType.MANUFACTURED: frozenset(
        {PhysicalLifecycleEventType.INSTALLED}
    ),
    PhysicalLifecycleEventType.INSTALLED: frozenset(
        {
            PhysicalLifecycleEventType.TESTED,
            PhysicalLifecycleEventType.FAILED,
            PhysicalLifecycleEventType.REMOVED,
        }
    ),
    PhysicalLifecycleEventType.TESTED: frozenset(
        {
            PhysicalLifecycleEventType.TESTED,
            PhysicalLifecycleEventType.ACTIVATED,
            PhysicalLifecycleEventType.FAILED,
            PhysicalLifecycleEventType.REMOVED,
        }
    ),
    PhysicalLifecycleEventType.ACTIVATED: frozenset(
        {
            PhysicalLifecycleEventType.FAILED,
            PhysicalLifecycleEventType.REMOVED,
        }
    ),
    PhysicalLifecycleEventType.FAILED: frozenset(
        {PhysicalLifecycleEventType.REMOVED}
    ),
    PhysicalLifecycleEventType.REMOVED: frozenset(
        {PhysicalLifecycleEventType.SUPERSEDED}
    ),
    PhysicalLifecycleEventType.SUPERSEDED: frozenset(),
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


def _validate_transition_history(
    timeline: tuple[PhysicalEventQueryResult, ...],
    event_types: tuple[PhysicalLifecycleEventType, ...],
) -> None:
    """Replay durable event semantics without inventing state from corrupt history."""

    if event_types[0] is not PhysicalLifecycleEventType.MANUFACTURED:
        raise LifecycleKnowledgeIntegrityError(
            "physical field-status timeline must start with MANUFACTURED"
        )

    for index, (event, event_type) in enumerate(zip(timeline, event_types)):
        if event_type is PhysicalLifecycleEventType.TESTED:
            try:
                PhysicalTestOutcome(event.test_outcome)
            except (TypeError, ValueError) as exc:
                raise LifecycleKnowledgeIntegrityError(
                    "physical field-status TESTED event requires PASSED or FAILED outcome"
                ) from exc

        if index == 0:
            continue

        previous_type = event_types[index - 1]
        if event_type not in _ALLOWED_NEXT_EVENTS[previous_type]:
            raise LifecycleKnowledgeIntegrityError(
                "physical field-status timeline contains impossible transition: "
                f"{previous_type.value} -> {event_type.value}"
            )

        if event_type is PhysicalLifecycleEventType.ACTIVATED:
            previous = timeline[index - 1]
            if previous_type is not PhysicalLifecycleEventType.TESTED:
                raise LifecycleKnowledgeIntegrityError(
                    "physical field-status ACTIVATED event must follow TESTED"
                )
            try:
                previous_outcome = PhysicalTestOutcome(previous.test_outcome)
            except (TypeError, ValueError) as exc:
                raise LifecycleKnowledgeIntegrityError(
                    "physical field-status activation requires a valid preceding test outcome"
                ) from exc
            if previous_outcome is not PhysicalTestOutcome.PASSED:
                raise LifecycleKnowledgeIntegrityError(
                    "physical field-status activation requires preceding PASSED test"
                )


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
    validated_event_types: list[PhysicalLifecycleEventType] = []

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

        try:
            event_type = PhysicalLifecycleEventType(event.event_type)
        except ValueError as exc:
            raise LifecycleKnowledgeIntegrityError(
                f"unsupported physical lifecycle event type: {event.event_type}"
            ) from exc
        if event_type not in _STATE_BY_EVENT:
            raise LifecycleKnowledgeIntegrityError(
                f"unsupported physical lifecycle event type: {event.event_type}"
            )
        validated_event_types.append(event_type)

        previous_sequence = event.sequence
        previous_time = event.occurred_at

    validated_event_type_tuple = tuple(validated_event_types)
    _validate_transition_history(timeline, validated_event_type_tuple)

    latest = timeline[-1]
    latest_event_type = validated_event_type_tuple[-1]

    return PhysicalFieldStatus(
        instance_id=latest.instance_id,
        revision_id=latest.revision_id,
        manufacturing_id=latest.manufacturing_id,
        state=_STATE_BY_EVENT[latest_event_type],
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
