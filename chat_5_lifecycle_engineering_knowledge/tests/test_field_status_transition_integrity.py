from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import (
    LifecycleKnowledgeIntegrityError,
    PhysicalPartState,
    build_physical_field_status,
)
from mrea_lifecycle.relational import PhysicalEventQueryResult


T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)


def _event(
    event_type: str,
    sequence: int,
    *,
    test_outcome: str | None = None,
) -> PhysicalEventQueryResult:
    return PhysicalEventQueryResult(
        event_id=f"PH-{sequence}",
        event_type=event_type,
        occurred_at=T0 + timedelta(minutes=sequence),
        sequence=sequence,
        instance_id="PI-X",
        revision_id="R-X",
        manufacturing_id="M-X",
        installation_id="I-X" if sequence > 1 else None,
        test_id=f"T-{sequence}" if event_type in {"TESTED", "ACTIVATED"} else None,
        failure_id=f"F-{sequence}" if event_type == "FAILED" else None,
        equipment_id="EQ-X" if sequence > 1 else None,
        position="A" if sequence > 1 else None,
        test_outcome=test_outcome,
        replacement_instance_id="PI-NEW" if event_type == "SUPERSEDED" else None,
        notes=None,
    )


def test_field_status_rejects_timeline_that_does_not_start_manufactured() -> None:
    with pytest.raises(LifecycleKnowledgeIntegrityError, match="start with MANUFACTURED"):
        build_physical_field_status((_event("INSTALLED", 1),))


def test_field_status_rejects_impossible_transition_with_known_event_types() -> None:
    with pytest.raises(LifecycleKnowledgeIntegrityError, match="MANUFACTURED -> ACTIVATED"):
        build_physical_field_status(
            (
                _event("MANUFACTURED", 1),
                _event("ACTIVATED", 2),
            )
        )


def test_field_status_rejects_tested_event_without_explicit_outcome() -> None:
    with pytest.raises(LifecycleKnowledgeIntegrityError, match="requires PASSED or FAILED"):
        build_physical_field_status(
            (
                _event("MANUFACTURED", 1),
                _event("INSTALLED", 2),
                _event("TESTED", 3),
            )
        )


def test_field_status_rejects_activation_after_failed_test() -> None:
    with pytest.raises(LifecycleKnowledgeIntegrityError, match="preceding PASSED"):
        build_physical_field_status(
            (
                _event("MANUFACTURED", 1),
                _event("INSTALLED", 2),
                _event("TESTED", 3, test_outcome="FAILED"),
                _event("ACTIVATED", 4),
            )
        )


def test_field_status_accepts_state_machine_legal_history() -> None:
    status = build_physical_field_status(
        (
            _event("MANUFACTURED", 1),
            _event("INSTALLED", 2),
            _event("TESTED", 3, test_outcome="PASSED"),
            _event("ACTIVATED", 4),
            _event("FAILED", 5),
            _event("REMOVED", 6),
            _event("SUPERSEDED", 7),
        )
    )

    assert status.state is PhysicalPartState.SUPERSEDED
    assert status.source_event_id == "PH-7"
    assert status.replacement_instance_id == "PI-NEW"
