from datetime import datetime, timedelta, timezone

from mrea_lifecycle import (
    EquipmentPartRegistry,
    FailureRecord,
    FailureService,
    InMemoryLifecycleStore,
    Installation,
    InstallationService,
    KnowledgeQueryService,
    LifecycleState,
    LifecycleStateProjection,
    LifecycleTimeline,
    ManufacturingRecord,
    ManufacturingService,
    Revision,
    RevisionComparison,
    RevisionService,
)


def test_rev01_failure_to_rev02_active_acceptance_flow() -> None:
    store = InMemoryLifecycleStore()
    revisions = RevisionService(store)
    manufacturing = ManufacturingService(store)
    installations = InstallationService(store)
    failures = FailureService(store)
    timeline = LifecycleTimeline(store)
    registry = EquipmentPartRegistry(store)
    states = LifecycleStateProjection(store, timeline, registry)
    comparison = RevisionComparison(store, states)
    knowledge = KnowledgeQueryService(store, registry)

    t0 = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)

    revisions.create(
        Revision(
            revision_id="R1",
            part_id="PART-0042",
            revision_code="REV01",
            created_at=t0,
            notes="Initial replacement geometry",
        ),
        event_id="E001",
    )
    manufacturing.record(
        ManufacturingRecord(
            manufacturing_id="MFG1",
            revision_id="R1",
            material="PETG",
            method="FDM",
            manufactured_at=t0 + timedelta(hours=1),
            machine="Printer-A",
        ),
        event_id="E002",
    )
    installations.install(
        Installation(
            installation_id="I1",
            revision_id="R1",
            manufacturing_id="MFG1",
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
            installed_at=t0 + timedelta(hours=2),
        ),
        event_id="E003",
    )
    failures.record(
        FailureRecord(
            failure_id="F1",
            revision_id="R1",
            manufacturing_id="MFG1",
            installation_id="I1",
            failed_at=t0 + timedelta(days=18),
            failure_type="CRACK",
            damage_location="near H2",
            circumstances="normal service",
            estimated_cause="stress concentration",
            confirmed_cause=None,
            related_feature="H2",
            evidence_artifact_ids=("ART-FAIL-001",),
        ),
        event_id="E004",
    )

    revisions.create(
        Revision(
            revision_id="R2",
            part_id="PART-0042",
            revision_code="REV02",
            parent_revision_id="R1",
            created_at=t0 + timedelta(days=19),
            notes="Increase wall and fillet near H2",
        ),
        event_id="E005",
    )
    manufacturing.record(
        ManufacturingRecord(
            manufacturing_id="MFG2",
            revision_id="R2",
            material="PETG",
            method="FDM",
            manufactured_at=t0 + timedelta(days=19, hours=1),
            machine="Printer-A",
        ),
        event_id="E006",
    )
    installations.install(
        Installation(
            installation_id="I2",
            revision_id="R2",
            manufacturing_id="MFG2",
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
            installed_at=t0 + timedelta(days=19, hours=2),
        ),
        event_id="E007",
    )

    assert states.for_revision("R1") is LifecycleState.FAILED
    assert states.for_revision("R2") is LifecycleState.ACTIVE
    assert knowledge.failed_revision_ids(part_id="PART-0042") == ("R1",)
    assert (
        knowledge.current_revision_for_equipment(
            equipment_id="FREEZER-01",
            position="INNER_DOOR_LEFT",
        )
        == "R2"
    )

    part_timeline = timeline.for_part("PART-0042")
    assert [event.event_id for event in part_timeline] == [
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
        "E006",
        "E007",
    ]
    assert store.failures["F1"].evidence_artifact_ids == ("ART-FAIL-001",)
    assert store.installations["I1"].revision_id == "R1"
    assert store.installations["I2"].revision_id == "R2"

    result = comparison.compare("R1", "R2")
    assert result.left_failure_count == 1
    assert result.right_failure_count == 0
    assert result.left_materials == ("PETG",)
    assert result.right_materials == ("PETG",)
    assert result.left_state is LifecycleState.FAILED
    assert result.right_state is LifecycleState.ACTIVE
