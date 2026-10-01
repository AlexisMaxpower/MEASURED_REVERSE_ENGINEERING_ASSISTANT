from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import (
    FailureRecord,
    Installation,
    LifecycleReadOnlyStaleError,
    LifecycleState,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
)


T0 = datetime(2026, 10, 1, 3, 30, tzinfo=timezone.utc)


def _seed_comparison_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-CMP", "REV01", T0), event_id="LC-R1"
        )
        uow.revisions.create(
            Revision(
                "R2",
                "PART-CMP",
                "REV02",
                T0 + timedelta(hours=1),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
        uow.revisions.create(
            Revision("R3", "OTHER-PART", "REV01", T0 + timedelta(hours=2)),
            event_id="LC-R3",
        )

        uow.manufacturing.record(
            ManufacturingRecord("M1", "R1", "PETG", "FDM", T0 + timedelta(hours=3)),
            event_id="LC-M1",
        )
        uow.manufacturing.record(
            ManufacturingRecord("M2", "R1", "TPU", "FDM", T0 + timedelta(hours=4)),
            event_id="LC-M2",
        )
        uow.manufacturing.record(
            ManufacturingRecord("M3", "R2", "ABS", "FDM", T0 + timedelta(hours=5)),
            event_id="LC-M3",
        )
        uow.manufacturing.record(
            ManufacturingRecord("M4", "R3", "PLA", "FDM", T0 + timedelta(hours=6)),
            event_id="LC-M4",
        )

        uow.installations.install(
            Installation(
                "I1",
                "R1",
                "M1",
                "EQ-1",
                "LEFT",
                T0 + timedelta(hours=7),
            ),
            event_id="LC-I1",
        )
        uow.tests.record(
            LifecycleTestRecord(
                "T1",
                "R1",
                T0 + timedelta(hours=8),
                "LOAD",
                "nominal",
                "pass",
                "accepted",
                manufacturing_id="M1",
                installation_id="I1",
            ),
            event_id="LC-T1",
        )
        uow.failures.record(
            FailureRecord(
                "F1",
                "R1",
                T0 + timedelta(hours=9),
                "CRACK",
                "HINGE",
                "service",
                ("EV-F1",),
                manufacturing_id="M1",
                installation_id="I1",
            ),
            event_id="LC-F1",
        )

        # A later installation/test preserves the original in-memory comparison
        # semantics: the revision is ACTIVE again even though its failure history stays.
        uow.installations.install(
            Installation(
                "I2",
                "R1",
                "M2",
                "EQ-2",
                "LEFT",
                T0 + timedelta(hours=10),
            ),
            event_id="LC-I2",
        )
        uow.tests.record(
            LifecycleTestRecord(
                "T2",
                "R1",
                T0 + timedelta(hours=11),
                "LOAD",
                "nominal",
                "pass",
                "accepted",
                manufacturing_id="M2",
                installation_id="I2",
            ),
            event_id="LC-T2",
        )
    store.close()


def test_durable_revision_comparison_preserves_existing_factual_semantics(tmp_path) -> None:
    database = tmp_path / "revision-comparison.db"
    _seed_comparison_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        comparison = session.knowledge.compare_revisions("R1", "R2")

    assert comparison.left_revision_id == "R1"
    assert comparison.right_revision_id == "R2"
    assert comparison.left_materials == ("PETG", "TPU")
    assert comparison.right_materials == ("ABS",)
    assert comparison.left_failure_count == 1
    assert comparison.right_failure_count == 0
    assert comparison.left_test_count == 2
    assert comparison.right_test_count == 0
    assert comparison.left_state is LifecycleState.ACTIVE
    assert comparison.right_state is LifecycleState.MANUFACTURED


def test_durable_revision_comparison_rejects_missing_or_cross_part_inputs(tmp_path) -> None:
    database = tmp_path / "revision-comparison-invalid.db"
    _seed_comparison_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        with pytest.raises(ValueError, match="both revisions must exist"):
            session.knowledge.compare_revisions("R1", "UNKNOWN")
        with pytest.raises(ValueError, match="different parts"):
            session.knowledge.compare_revisions("R1", "R3")


def test_durable_revision_comparison_fails_closed_after_snapshot_drift(tmp_path) -> None:
    database = tmp_path / "revision-comparison-stale.db"
    _seed_comparison_database(database)

    session = SQLiteLifecycleReadOnlySession(database)
    writer = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(writer)
    with uow.transaction():
        uow.tests.record(
            LifecycleTestRecord(
                "T-R2",
                "R2",
                T0 + timedelta(hours=12),
                "LOAD",
                "nominal",
                "pass",
                "accepted",
                manufacturing_id="M3",
            ),
            event_id="LC-T-R2",
        )
    writer.close()

    with pytest.raises(LifecycleReadOnlyStaleError, match="refresh required"):
        session.knowledge.compare_revisions("R1", "R2")

    session.refresh()
    comparison = session.knowledge.compare_revisions("R1", "R2")
    assert comparison.right_test_count == 1
    assert comparison.right_state is LifecycleState.ACTIVE
    session.close()
