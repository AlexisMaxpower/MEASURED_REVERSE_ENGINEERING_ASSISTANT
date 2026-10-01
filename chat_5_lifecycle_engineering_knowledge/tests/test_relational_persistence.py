from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

import mrea_lifecycle.persistence as persistence_module
from mrea_lifecycle import (
    FailureRecord,
    Installation,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalTestOutcome,
    Revision,
    SQLiteLifecycleStore,
    SQLITE_RELATIONAL_SCHEMA_VERSION,
    TestRecord as LifecycleTestRecord,
)


T0 = datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc)


def _create_legacy_pass4_database(path) -> None:
    payload = {
        "revisions": {
            "R-LEGACY": {
                "revision_id": "R-LEGACY",
                "part_id": "PART-LEGACY",
                "revision_code": "REV01",
                "created_at": {
                    "$type": "datetime",
                    "value": T0.isoformat(),
                },
                "parent_revision_id": None,
                "notes": "created by Pass 4",
                "source_cad_artifact_id": None,
                "origin": "MANUAL",
                "cad_link": None,
            }
        },
        "manufacturing_records": {},
        "installations": {},
        "tests": {},
        "failures": {},
        "events": [
            {
                "event_id": "LC-LEGACY-R1",
                "event_type": "REVISION_CREATED",
                "occurred_at": {
                    "$type": "datetime",
                    "value": T0.isoformat(),
                },
                "sequence": 1,
                "revision_id": "R-LEGACY",
                "manufacturing_id": None,
                "installation_id": None,
                "test_id": None,
                "failure_id": None,
            }
        ],
        "physical_instances": {},
        "physical_events": [],
    }

    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE lifecycle_store (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            schema_version TEXT NOT NULL,
            version INTEGER NOT NULL CHECK (version >= 0),
            payload TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO lifecycle_store(singleton, schema_version, version, payload)
        VALUES (1, 'mrea.lifecycle-snapshot.v1', 4, ?)
        """,
        (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
    )
    connection.commit()
    connection.close()


def _build_active_instance(store: SQLiteLifecycleStore) -> LifecycleUnitOfWork:
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-0042",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-R1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M1",
                revision_id="R1",
                material="PETG",
                method="FDM",
                manufactured_at=T0 + timedelta(hours=1),
                batch="BATCH-01",
            ),
            event_id="LC-M1",
        )
        uow.physical.register_manufactured(
            instance_id="PI-001",
            manufacturing_id="M1",
            physical_event_id="PH-M1",
        )
        uow.physical.install(
            Installation(
                installation_id="I1",
                revision_id="R1",
                manufacturing_id="M1",
                equipment_id="RACK-01",
                position="SLOT-A",
                installed_at=T0 + timedelta(hours=2),
                instance_id="PI-001",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                test_id="T1",
                revision_id="R1",
                tested_at=T0 + timedelta(hours=3),
                test_type="FIT_AND_LOAD",
                conditions="installed",
                result="pass",
                conclusion="accepted",
                manufacturing_id="M1",
                installation_id="I1",
                artifact_ids=("ART-T1",),
                instance_id="PI-001",
            ),
            outcome=PhysicalTestOutcome.PASSED,
            lifecycle_event_id="LC-T1",
            physical_event_id="PH-T1",
        )
        uow.physical.activate(
            instance_id="PI-001",
            activated_at=T0 + timedelta(hours=4),
            physical_event_id="PH-ACTIVE-1",
        )
    return uow


def test_pass4_database_migrates_and_backfills_without_snapshot_rewrite(tmp_path) -> None:
    database = tmp_path / "legacy-pass4.db"
    _create_legacy_pass4_database(database)

    store = SQLiteLifecycleStore(database)

    assert store.loaded_version == 4
    assert store.read_model_version == 4
    assert store.relational_schema_version == SQLITE_RELATIONAL_SCHEMA_VERSION == 4
    assert "R-LEGACY" in store.revisions

    history = store.queries.revision_history("PART-LEGACY")
    assert [item.revision_id for item in history] == ["R-LEGACY"]
    assert history[0].revision_code == "REV01"
    assert history[0].runtime_status is None
    store.close()

    connection = sqlite3.connect(database)
    rows = connection.execute(
        "SELECT version, name FROM lifecycle_schema_migrations ORDER BY version"
    ).fetchall()
    snapshot = connection.execute(
        "SELECT version, schema_version FROM lifecycle_store WHERE singleton = 1"
    ).fetchone()
    connection.close()

    assert rows == [
        (2, "normalized_lifecycle_read_model"),
        (3, "cad_runtime_truth"),
        (4, "materialized_engineering_knowledge"),
    ]
    assert snapshot == (4, "mrea.lifecycle-snapshot.v1")

    reopened = SQLiteLifecycleStore(database)
    assert reopened.relational_schema_version == 4
    assert reopened.read_model_version == 4
    assert len(reopened.queries.revision_history("PART-LEGACY")) == 1
    reopened.close()


def test_relational_queries_follow_committed_physical_lifecycle(tmp_path) -> None:
    database = tmp_path / "queries.db"
    store = SQLiteLifecycleStore(database)
    uow = _build_active_instance(store)

    assert store.loaded_version == store.read_model_version == 1
    assert [item.revision_id for item in store.queries.revision_history("PART-0042")] == [
        "R1"
    ]

    active = store.queries.equipment_occupancy(equipment_id="RACK-01")
    assert len(active) == 1
    assert active[0].instance_id == "PI-001"
    assert active[0].position == "SLOT-A"
    assert active[0].state == "ACTIVE"

    timeline = store.queries.physical_timeline("PI-001")
    assert [item.event_type for item in timeline] == [
        "MANUFACTURED",
        "INSTALLED",
        "TESTED",
        "ACTIVATED",
    ]
    assert [item.sequence for item in timeline] == [1, 2, 3, 4]

    with uow.transaction():
        uow.physical.fail(
            FailureRecord(
                failure_id="F1",
                revision_id="R1",
                failed_at=T0 + timedelta(hours=5),
                failure_type="CRACK",
                damage_location="HINGE",
                circumstances="load cycle",
                evidence_artifact_ids=("ART-F1-A", "ART-F1-B"),
                manufacturing_id="M1",
                installation_id="I1",
                confirmed_cause="thin wall",
                instance_id="PI-001",
            ),
            lifecycle_event_id="LC-F1",
            physical_event_id="PH-F1",
        )

    assert store.loaded_version == store.read_model_version == 2
    failures = store.queries.failure_history(instance_id="PI-001")
    assert len(failures) == 1
    assert failures[0].failure_id == "F1"
    assert failures[0].confirmed_cause == "thin wall"
    assert failures[0].equipment_id == "RACK-01"
    assert failures[0].position == "SLOT-A"

    failed_occupancy = store.queries.equipment_occupancy(
        equipment_id="RACK-01", position="SLOT-A"
    )
    assert len(failed_occupancy) == 1
    assert failed_occupancy[0].state == "FAILED"

    with uow.transaction():
        uow.physical.remove(
            instance_id="PI-001",
            removed_at=T0 + timedelta(hours=6),
            physical_event_id="PH-REMOVED-1",
            reason="replace damaged part",
        )

    assert store.loaded_version == store.read_model_version == 3
    assert store.queries.equipment_occupancy(equipment_id="RACK-01") == ()
    store.close()


def test_read_model_failure_rolls_back_snapshot_and_relational_state(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "atomic-read-model.db"
    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)

    assert store.loaded_version == store.read_model_version == 0

    def explode(connection, repository):
        raise RuntimeError("forced read model failure")

    monkeypatch.setattr(
        persistence_module.SQLiteLifecycleReadModelWriter,
        "replace",
        explode,
    )

    with pytest.raises(RuntimeError, match="forced read model failure"):
        with uow.transaction():
            uow.revisions.create(
                Revision(
                    revision_id="R1",
                    part_id="PART-0042",
                    revision_code="REV01",
                    created_at=T0,
                ),
                event_id="LC-R1",
            )

    assert store.loaded_version == 0
    assert store.revisions == {}
    assert store.queries.revision_history("PART-0042") == ()
    assert store.read_model_version == 0
    store.close()

    reopened = SQLiteLifecycleStore(database)
    assert reopened.loaded_version == reopened.read_model_version == 0
    assert reopened.revisions == {}
    assert reopened.queries.revision_history("PART-0042") == ()
    reopened.close()


def test_reopen_repairs_stale_or_damaged_relational_projection(tmp_path) -> None:
    database = tmp_path / "repair.db"
    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)

    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-REPAIR",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-R1",
        )

    assert store.loaded_version == store.read_model_version == 1
    store.close()

    connection = sqlite3.connect(database)
    connection.execute("DELETE FROM lifecycle_revisions")
    connection.execute(
        "UPDATE lifecycle_read_model_meta SET snapshot_version = 0 WHERE singleton = 1"
    )
    connection.commit()
    connection.close()

    repaired = SQLiteLifecycleStore(database)
    assert repaired.loaded_version == repaired.read_model_version == 1
    history = repaired.queries.revision_history("PART-REPAIR")
    assert [item.revision_id for item in history] == ["R1"]
    repaired.close()


def test_relational_schema_does_not_invent_one_instance_per_manufacturing_rule(
    tmp_path,
) -> None:
    database = tmp_path / "batch.db"
    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)

    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-BATCH",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-R1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M-BATCH",
                revision_id="R1",
                material="PA12",
                method="SLS",
                manufactured_at=T0 + timedelta(hours=1),
                batch="BATCH-100",
            ),
            event_id="LC-M1",
        )
        uow.physical.register_manufactured(
            instance_id="PI-A",
            manufacturing_id="M-BATCH",
            physical_event_id="PH-A",
        )
        uow.physical.register_manufactured(
            instance_id="PI-B",
            manufacturing_id="M-BATCH",
            physical_event_id="PH-B",
        )

    assert set(store.physical_instances) == {"PI-A", "PI-B"}
    assert [item.event_id for item in store.queries.physical_timeline("PI-A")] == [
        "PH-A"
    ]
    assert [item.event_id for item in store.queries.physical_timeline("PI-B")] == [
        "PH-B"
    ]
    assert store.loaded_version == store.read_model_version == 1
    store.close()
