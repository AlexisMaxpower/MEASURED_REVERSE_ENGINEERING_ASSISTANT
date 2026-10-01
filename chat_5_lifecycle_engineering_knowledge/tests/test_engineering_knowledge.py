from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from mrea_lifecycle import (
    FailureRecord,
    Installation,
    LifecycleKnowledgeIntegrityError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalTestOutcome,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
)


T0 = datetime(2026, 9, 30, 6, 0, tzinfo=timezone.utc)


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-KNOW", "REV01", T0), event_id="LC-R1"
        )
        uow.revisions.create(
            Revision(
                "R2",
                "PART-KNOW",
                "REV02",
                T0 + timedelta(hours=1),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
        uow.revisions.create(
            Revision(
                "R3",
                "PART-KNOW",
                "REV03",
                T0 + timedelta(hours=2),
                parent_revision_id="R2",
            ),
            event_id="LC-R3",
        )

        for record, event_id in (
            (
                ManufacturingRecord(
                    "M1", "R1", "PETG", "FDM", T0 + timedelta(hours=3)
                ),
                "LC-M1",
            ),
            (
                ManufacturingRecord(
                    "M2", "R2", "PETG", "FDM", T0 + timedelta(hours=4)
                ),
                "LC-M2",
            ),
            (
                ManufacturingRecord(
                    "M3", "R1", "PETG", "FDM", T0 + timedelta(hours=5)
                ),
                "LC-M3",
            ),
        ):
            uow.manufacturing.record(record, event_id=event_id)

        uow.physical.register_manufactured(
            instance_id="PI-1", manufacturing_id="M1", physical_event_id="PH-M1"
        )
        uow.physical.register_manufactured(
            instance_id="PI-2", manufacturing_id="M2", physical_event_id="PH-M2"
        )
        uow.physical.register_manufactured(
            instance_id="PI-3", manufacturing_id="M3", physical_event_id="PH-M3"
        )

        uow.physical.install(
            Installation(
                "I1",
                "R1",
                "M1",
                "EQ-01",
                "LEFT",
                T0 + timedelta(hours=6),
                instance_id="PI-1",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T1",
                "R1",
                T0 + timedelta(hours=7),
                "LOAD",
                "nominal",
                "pass",
                "accepted",
                manufacturing_id="M1",
                installation_id="I1",
                instance_id="PI-1",
            ),
            outcome=PhysicalTestOutcome.PASSED,
            lifecycle_event_id="LC-T1",
            physical_event_id="PH-T1",
        )
        uow.physical.activate(
            instance_id="PI-1",
            activated_at=T0 + timedelta(hours=8),
            physical_event_id="PH-A1",
        )
        uow.physical.fail(
            FailureRecord(
                "F1",
                "R1",
                T0 + timedelta(hours=9),
                "CRACK",
                "HINGE_ROOT",
                "normal service",
                ("EV-F1",),
                manufacturing_id="M1",
                installation_id="I1",
                confirmed_cause="FATIGUE",
                instance_id="PI-1",
            ),
            lifecycle_event_id="LC-F1",
            physical_event_id="PH-F1",
        )
        uow.physical.remove(
            instance_id="PI-1",
            removed_at=T0 + timedelta(hours=10),
            physical_event_id="PH-RM1",
            reason="replace failed instance",
        )

        uow.physical.install(
            Installation(
                "I2",
                "R2",
                "M2",
                "EQ-01",
                "LEFT",
                T0 + timedelta(hours=11),
                instance_id="PI-2",
            ),
            lifecycle_event_id="LC-I2",
            physical_event_id="PH-I2",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T2",
                "R2",
                T0 + timedelta(hours=12),
                "LOAD",
                "nominal",
                "pass",
                "accepted",
                manufacturing_id="M2",
                installation_id="I2",
                instance_id="PI-2",
            ),
            outcome=PhysicalTestOutcome.PASSED,
            lifecycle_event_id="LC-T2",
            physical_event_id="PH-T2",
        )
        uow.physical.activate(
            instance_id="PI-2",
            activated_at=T0 + timedelta(hours=13),
            physical_event_id="PH-A2",
        )
        uow.physical.supersede(
            instance_id="PI-1",
            replacement_instance_id="PI-2",
            superseded_at=T0 + timedelta(hours=14),
            physical_event_id="PH-S1",
        )

        uow.physical.install(
            Installation(
                "I3",
                "R1",
                "M3",
                "EQ-02",
                "LEFT",
                T0 + timedelta(hours=15),
                instance_id="PI-3",
            ),
            lifecycle_event_id="LC-I3",
            physical_event_id="PH-I3",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T3",
                "R1",
                T0 + timedelta(hours=16),
                "LOAD",
                "nominal",
                "pass",
                "accepted",
                manufacturing_id="M3",
                installation_id="I3",
                instance_id="PI-3",
            ),
            outcome=PhysicalTestOutcome.PASSED,
            lifecycle_event_id="LC-T3",
            physical_event_id="PH-T3",
        )
        uow.physical.activate(
            instance_id="PI-3",
            activated_at=T0 + timedelta(hours=17),
            physical_event_id="PH-A3",
        )
        uow.physical.fail(
            FailureRecord(
                "F2",
                "R1",
                T0 + timedelta(hours=18),
                "CRACK",
                "HINGE_ROOT",
                "normal service",
                ("EV-F2",),
                manufacturing_id="M3",
                installation_id="I3",
                confirmed_cause="FATIGUE",
                instance_id="PI-3",
            ),
            lifecycle_event_id="LC-F2",
            physical_event_id="PH-F2",
        )
        uow.physical.remove(
            instance_id="PI-3",
            removed_at=T0 + timedelta(hours=19),
            physical_event_id="PH-RM3",
            reason="failed",
        )
    store.close()


def test_revision_lineage_and_outcomes_are_factual_and_deterministic(tmp_path) -> None:
    database = tmp_path / "knowledge.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        lineage = session.knowledge.revision_lineage("PART-KNOW")
        assert [(item.revision_id, item.depth) for item in lineage] == [
            ("R1", 0),
            ("R2", 1),
            ("R3", 2),
        ]

        outcomes = session.knowledge.revision_outcomes("PART-KNOW")
        by_revision = {item.revision_id: item for item in outcomes}
        assert by_revision["R1"].manufacturing_records == 2
        assert by_revision["R1"].physical_instances == 2
        assert by_revision["R1"].activated_instances == 2
        assert by_revision["R1"].failed_instances == 2
        assert by_revision["R1"].removed_instances == 2
        assert by_revision["R1"].superseded_instances == 1
        assert by_revision["R1"].failure_records == 2
        assert by_revision["R2"].physical_instances == 1
        assert by_revision["R2"].failed_instances == 0
        assert by_revision["R3"].physical_instances == 0


def test_equipment_history_and_replacement_chain_preserve_exact_instances(tmp_path) -> None:
    database = tmp_path / "equipment.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        history = session.knowledge.equipment_position_history(
            equipment_id="EQ-01", position="LEFT"
        )
        assert [item.instance_id for item in history] == [
            "PI-1",
            "PI-1",
            "PI-1",
            "PI-1",
            "PI-1",
            "PI-2",
            "PI-2",
            "PI-2",
            "PI-1",
        ]
        assert history[-1].event_type == "SUPERSEDED"
        assert history[-1].replacement_instance_id == "PI-2"

        chain = session.knowledge.replacement_chain("PI-1")
        assert [item.instance_id for item in chain] == ["PI-1", "PI-2"]
        assert chain[0].state == "SUPERSEDED"
        assert chain[0].replacement_instance_id == "PI-2"
        assert chain[1].state == "ACTIVE"
        assert chain[1].replacement_instance_id is None


def test_failure_patterns_group_only_matching_recorded_facts(tmp_path) -> None:
    database = tmp_path / "failures.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        patterns = session.knowledge.failure_patterns(part_id="PART-KNOW")
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.failure_type == "CRACK"
        assert pattern.damage_location == "HINGE_ROOT"
        assert pattern.confirmed_cause == "FATIGUE"
        assert pattern.occurrence_count == 2
        assert pattern.revision_count == 1
        assert pattern.instance_count == 2
        assert pattern.first_failed_at == T0 + timedelta(hours=9)
        assert pattern.last_failed_at == T0 + timedelta(hours=18)

        assert session.knowledge.failure_patterns(revision_id="R2") == ()


def test_lineage_cycle_is_detected_fail_closed(tmp_path) -> None:
    database = tmp_path / "cycle.db"
    _seed_database(database)

    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE lifecycle_revisions SET parent_revision_id = 'R3' WHERE revision_id = 'R1'"
    )
    connection.commit()
    connection.close()

    with SQLiteLifecycleReadOnlySession(database) as session:
        with pytest.raises(LifecycleKnowledgeIntegrityError, match="cycle detected"):
            session.knowledge.revision_lineage("PART-KNOW")
