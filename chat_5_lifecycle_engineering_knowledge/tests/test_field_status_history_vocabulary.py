from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import LifecycleKnowledgeIntegrityError, build_physical_field_status
from mrea_lifecycle.relational import PhysicalEventQueryResult


T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)


def _event(*, event_id: str, event_type: str, sequence: int, occurred_at: datetime) -> PhysicalEventQueryResult:
    return PhysicalEventQueryResult(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        sequence=sequence,
        instance_id="PI-X",
        revision_id="R-X",
        manufacturing_id="M-X",
        installation_id=None,
        test_id=None,
        failure_id=None,
        equipment_id=None,
        position=None,
        test_outcome=None,
        replacement_instance_id=None,
        notes=None,
    )


def test_field_status_rejects_unknown_event_type_before_valid_latest_event() -> None:
    timeline = (
        _event(
            event_id="PH-CORRUPT",
            event_type="UNKNOWN_EVENT",
            sequence=1,
            occurred_at=T0,
        ),
        _event(
            event_id="PH-ACTIVE",
            event_type="ACTIVATED",
            sequence=2,
            occurred_at=T0 + timedelta(minutes=1),
        ),
    )

    with pytest.raises(
        LifecycleKnowledgeIntegrityError,
        match="unsupported physical lifecycle event type: UNKNOWN_EVENT",
    ):
        build_physical_field_status(timeline)
