from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import (
    CanonicalLifecycleEventAdapter,
    FailureRecord,
    InMemoryLifecycleStore,
    Installation,
    LifecycleInvariantError,
    ManufacturingRecord,
    ManufacturingService,
    PhysicalEquipmentRegistry,
    PhysicalLifecycleEventType,
    PhysicalPartLifecycleService,
    PhysicalPartState,
    PhysicalPartStateProjection,
    PhysicalPartTimeline,
    PhysicalTestOutcome,
    Revision,
    RevisionService,
    TestRecord as LifecycleTestRecord,
)


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)


def _manufactured_instance(
    *,
    store: InMemoryLifecycleStore,
    lifecycle: PhysicalPartLifecycleService,
    revision_id: str,
    revision_code: str,
    manufacturing_id: str,
    instance_id: str,
    created_at: datetime,
    manufactured_at: datetime,
) -> None:
    RevisionService(store).create(
        Revision(
            revision_id=revision_id,
            part_id="PART-0042",
            revision_code=revision_code,
            created_at=created_at,
        ),
        event_id=f"LC-{revision_id}-CREATED",
    )
    ManufacturingService(store).record(
        ManufacturingRecord(
            manufacturing_id=manufacturing_id,
            revision_id=revision_id,
            material="PETG",
            method="FDM",
            manufactured_at=manufactured_at,
            machine="Printer-A",
            batch="BATCH-01",
        ),
        event_id=f"LC-{manufacturing_id}-MANUFACTURED",
    )
    lifecycle.register_manufactured(
        instance_id=instance_id,
        manufacturing_id=manufacturing_id,
        physical_event_id=f"PH-{instance_id}-MANUFACTURED",
    )


def test_physical_instance_full_lifecycle_failure_removal_and_replacement() -> None:
    store = InMemoryLifecycleStore()
    lifecycle = PhysicalPartLifecycleService(store)
    states = PhysicalPartStateProjection(store)
    timeline = PhysicalPartTimeline(store)
    registry = PhysicalEquipmentRegistry(store)

    _manufactured_instance(
        store=store,
        lifecycle=lifecycle,
        revision_id="R1",
        revision_code="REV01",
        manufacturing_id="M1",
        instance_id="PI-001",
        created_at=T0,
        manufactured_at=T0 + timedelta(hours=1),
    )

    instance = store.physical_instances["PI-001"]
    assert instance.revision_id == "R1"
    assert instance.manufacturing_id == "M1"
    assert instance.material == "PETG"
    assert instance.method == "FDM"
    assert instance.machine == "Printer-A"
    assert states.for_instance("PI-001") is PhysicalPartState.MANUFACTURED

    lifecycle.install(
        Installation(
            installation_id="I1",
            revision_id="R1",
            manufacturing_id="M1",
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
            installed_at=T0 + timedelta(hours=2),
            instance_id="PI-001",
        ),
        lifecycle_event_id="LC-I1",
        physical_event_id="PH-I1",
    )
    assert states.for_instance("PI-001") is PhysicalPartState.INSTALLED

    lifecycle.test(
        LifecycleTestRecord(
            test_id="T1",
            revision_id="R1",
            manufacturing_id="M1",
            installation_id="I1",
            instance_id="PI-001",
            tested_at=T0 + timedelta(hours=3),
            test_type="FIT_AND_LOAD",
            conditions="installed on target equipment",
            result="pass",
            conclusion="fit and load acceptable",
            artifact_ids=("ART-TEST-001",),
        ),
        outcome=PhysicalTestOutcome.PASSED,
        lifecycle_event_id="LC-T1",
        physical_event_id="PH-T1",
    )
    assert states.for_instance("PI-001") is PhysicalPartState.TESTED

    lifecycle.activate(
        instance_id="PI-001",
        activated_at=T0 + timedelta(hours=4),
        physical_event_id="PH-ACTIVE-1",
    )
    assert states.for_instance("PI-001") is PhysicalPartState.ACTIVE
    assert (
        registry.current_instance(
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
        ).instance_id
        == "PI-001"
    )

    lifecycle.fail(
        FailureRecord(
            failure_id="F1",
            revision_id="R1",
            manufacturing_id="M1",
            installation_id="I1",
            instance_id="PI-001",
            failed_at=T0 + timedelta(days=10),
            failure_type="CRACK",
            damage_location="near H2",
            circumstances="normal service",
            evidence_artifact_ids=("ART-FAIL-001", "ART-FAIL-002"),
            estimated_cause="stress concentration",
            related_feature="H2",
        ),
        lifecycle_event_id="LC-F1",
        physical_event_id="PH-F1",
    )
    assert states.for_instance("PI-001") is PhysicalPartState.FAILED
    assert store.failures["F1"].instance_id == "PI-001"
    assert store.failures["F1"].revision_id == "R1"
    assert store.failures["F1"].evidence_artifact_ids == (
        "ART-FAIL-001",
        "ART-FAIL-002",
    )

    lifecycle.remove(
        instance_id="PI-001",
        removed_at=T0 + timedelta(days=10, hours=1),
        physical_event_id="PH-REMOVE-1",
        reason="failed part removed for replacement",
    )
    assert states.for_instance("PI-001") is PhysicalPartState.REMOVED
    assert (
        registry.current_instance(
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
        )
        is None
    )

    _manufactured_instance(
        store=store,
        lifecycle=lifecycle,
        revision_id="R2",
        revision_code="REV02",
        manufacturing_id="M2",
        instance_id="PI-002",
        created_at=T0 + timedelta(days=10, hours=2),
        manufactured_at=T0 + timedelta(days=10, hours=3),
    )

    lifecycle.install(
        Installation(
            installation_id="I2",
            revision_id="R2",
            manufacturing_id="M2",
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
            installed_at=T0 + timedelta(days=10, hours=4),
            instance_id="PI-002",
        ),
        lifecycle_event_id="LC-I2",
        physical_event_id="PH-I2",
    )
    lifecycle.test(
        LifecycleTestRecord(
            test_id="T2",
            revision_id="R2",
            manufacturing_id="M2",
            installation_id="I2",
            instance_id="PI-002",
            tested_at=T0 + timedelta(days=10, hours=5),
            test_type="FIT_AND_LOAD",
            conditions="replacement installed",
            result="pass",
            conclusion="replacement accepted",
        ),
        outcome=PhysicalTestOutcome.PASSED,
        lifecycle_event_id="LC-T2",
        physical_event_id="PH-T2",
    )
    lifecycle.activate(
        instance_id="PI-002",
        activated_at=T0 + timedelta(days=10, hours=6),
        physical_event_id="PH-ACTIVE-2",
    )

    lifecycle.supersede(
        instance_id="PI-001",
        replacement_instance_id="PI-002",
        superseded_at=T0 + timedelta(days=10, hours=7),
        physical_event_id="PH-SUPERSEDE-1",
        notes="PI-002 replaced PI-001",
    )

    assert states.for_instance("PI-001") is PhysicalPartState.SUPERSEDED
    assert states.for_instance("PI-002") is PhysicalPartState.ACTIVE
    assert (
        registry.current_instance(
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
        ).instance_id
        == "PI-002"
    )

    assert [event.event_type for event in timeline.for_instance("PI-001")] == [
        PhysicalLifecycleEventType.MANUFACTURED,
        PhysicalLifecycleEventType.INSTALLED,
        PhysicalLifecycleEventType.TESTED,
        PhysicalLifecycleEventType.ACTIVATED,
        PhysicalLifecycleEventType.FAILED,
        PhysicalLifecycleEventType.REMOVED,
        PhysicalLifecycleEventType.SUPERSEDED,
    ]
    assert timeline.for_instance("PI-001")[-1].replacement_instance_id == "PI-002"

    canonical = CanonicalLifecycleEventAdapter().export(store.events)
    assert {event["event_type"] for event in canonical} <= {
        "REVISION_CREATED",
        "MANUFACTURED",
        "INSTALLED",
        "TESTED",
        "FAILED",
    }
    assert all("instance_id" not in event for event in canonical)


def test_invalid_physical_transitions_and_occupied_position_are_rejected() -> None:
    store = InMemoryLifecycleStore()
    lifecycle = PhysicalPartLifecycleService(store)

    _manufactured_instance(
        store=store,
        lifecycle=lifecycle,
        revision_id="R1",
        revision_code="REV01",
        manufacturing_id="M1",
        instance_id="PI-001",
        created_at=T0,
        manufactured_at=T0 + timedelta(hours=1),
    )

    with pytest.raises(LifecycleInvariantError, match="TESTED before activation"):
        lifecycle.activate(
            instance_id="PI-001",
            activated_at=T0 + timedelta(hours=2),
            physical_event_id="PH-ACTIVE-EARLY",
        )

    lifecycle.install(
        Installation(
            installation_id="I1",
            revision_id="R1",
            manufacturing_id="M1",
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
            installed_at=T0 + timedelta(hours=2),
            instance_id="PI-001",
        ),
        lifecycle_event_id="LC-I1",
        physical_event_id="PH-I1",
    )

    lifecycle.test(
        LifecycleTestRecord(
            test_id="T1",
            revision_id="R1",
            manufacturing_id="M1",
            installation_id="I1",
            instance_id="PI-001",
            tested_at=T0 + timedelta(hours=3),
            test_type="FIT",
            conditions="installed",
            result="fail",
            conclusion="requires rework",
        ),
        outcome=PhysicalTestOutcome.FAILED,
        lifecycle_event_id="LC-T1",
        physical_event_id="PH-T1",
    )

    with pytest.raises(LifecycleInvariantError, match="latest physical test must be PASSED"):
        lifecycle.activate(
            instance_id="PI-001",
            activated_at=T0 + timedelta(hours=4),
            physical_event_id="PH-ACTIVE-FAILED-TEST",
        )

    with pytest.raises(LifecycleInvariantError, match="backward in time"):
        lifecycle.remove(
            instance_id="PI-001",
            removed_at=T0 + timedelta(hours=2, minutes=30),
            physical_event_id="PH-BACKWARD",
            reason="invalid chronology",
        )

    RevisionService(store).create(
        Revision(
            revision_id="R2",
            part_id="PART-0042",
            revision_code="REV02",
            created_at=T0 + timedelta(hours=4),
        ),
        event_id="LC-R2-CREATED",
    )
    ManufacturingService(store).record(
        ManufacturingRecord(
            manufacturing_id="M2",
            revision_id="R2",
            material="PETG",
            method="FDM",
            manufactured_at=T0 + timedelta(hours=5),
        ),
        event_id="LC-M2-MANUFACTURED",
    )
    lifecycle.register_manufactured(
        instance_id="PI-002",
        manufacturing_id="M2",
        physical_event_id="PH-PI-002-MANUFACTURED",
    )

    with pytest.raises(LifecycleInvariantError, match="already occupied"):
        lifecycle.install(
            Installation(
                installation_id="I2",
                revision_id="R2",
                manufacturing_id="M2",
                equipment_id="FREEZER-01",
                position="INNER_DOOR_LEFT",
                installed_at=T0 + timedelta(hours=6),
                instance_id="PI-002",
            ),
            lifecycle_event_id="LC-I2",
            physical_event_id="PH-I2",
        )

    assert "I2" not in store.installations
    assert all(event.installation_id != "I2" for event in store.events)

    with pytest.raises(LifecycleInvariantError, match="REMOVED before superseding"):
        lifecycle.supersede(
            instance_id="PI-001",
            replacement_instance_id="PI-002",
            superseded_at=T0 + timedelta(hours=7),
            physical_event_id="PH-SUPERSEDE-EARLY",
        )
