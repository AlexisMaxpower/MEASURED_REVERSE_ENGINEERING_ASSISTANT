from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import (
    FailureRecord,
    Installation,
    LifecycleKnowledgeCursorError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalTestOutcome,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
)


T0 = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        previous = None
        for index in range(1, 6):
            revision_id = f"R{index}"
            uow.revisions.create(
                Revision(
                    revision_id,
                    "PART-PAGE",
                    f"REV{index:02d}",
                    T0 + timedelta(minutes=index),
                    parent_revision_id=previous,
                ),
                event_id=f"LC-{revision_id}",
            )
            previous = revision_id

        for record, event_id in (
            (
                ManufacturingRecord(
                    "M1", "R1", "PETG", "FDM", T0 + timedelta(hours=1)
                ),
                "LC-M1",
            ),
            (
                ManufacturingRecord(
                    "M2", "R2", "PETG", "FDM", T0 + timedelta(hours=2)
                ),
                "LC-M2",
            ),
            (
                ManufacturingRecord(
                    "M3", "R1", "PETG", "FDM", T0 + timedelta(hours=3)
                ),
                "LC-M3",
            ),
        ):
            uow.manufacturing.record(record, event_id=event_id)

        for instance_id, manufacturing_id, physical_event_id in (
            ("PI-1", "M1", "PH-M1"),
            ("PI-2", "M2", "PH-M2"),
            ("PI-3", "M3", "PH-M3"),
        ):
            uow.physical.register_manufactured(
                instance_id=instance_id,
                manufacturing_id=manufacturing_id,
                physical_event_id=physical_event_id,
            )

        uow.physical.install(
            Installation(
                "I1",
                "R1",
                "M1",
                "EQ-PAGE",
                "LEFT",
                T0 + timedelta(hours=4),
                instance_id="PI-1",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T1",
                "R1",
                T0 + timedelta(hours=5),
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
            activated_at=T0 + timedelta(hours=6),
            physical_event_id="PH-A1",
        )
        uow.physical.fail(
            FailureRecord(
                "F1",
                "R1",
                T0 + timedelta(hours=7),
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
            removed_at=T0 + timedelta(hours=8),
            physical_event_id="PH-RM1",
            reason="replace",
        )

        uow.physical.install(
            Installation(
                "I2",
                "R2",
                "M2",
                "EQ-PAGE",
                "LEFT",
                T0 + timedelta(hours=9),
                instance_id="PI-2",
            ),
            lifecycle_event_id="LC-I2",
            physical_event_id="PH-I2",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T2",
                "R2",
                T0 + timedelta(hours=10),
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
            activated_at=T0 + timedelta(hours=11),
            physical_event_id="PH-A2",
        )
        uow.physical.supersede(
            instance_id="PI-1",
            replacement_instance_id="PI-2",
            superseded_at=T0 + timedelta(hours=12),
            physical_event_id="PH-S1",
        )

        uow.physical.install(
            Installation(
                "I3",
                "R1",
                "M3",
                "EQ-OTHER",
                "RIGHT",
                T0 + timedelta(hours=13),
                instance_id="PI-3",
            ),
            lifecycle_event_id="LC-I3",
            physical_event_id="PH-I3",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T3",
                "R1",
                T0 + timedelta(hours=14),
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
            activated_at=T0 + timedelta(hours=15),
            physical_event_id="PH-A3",
        )
        uow.physical.fail(
            FailureRecord(
                "F2",
                "R1",
                T0 + timedelta(hours=16),
                "DEFORMATION",
                "MOUNT_FACE",
                "overload",
                ("EV-F2",),
                manufacturing_id="M3",
                installation_id="I3",
                confirmed_cause="OVERLOAD",
                instance_id="PI-3",
            ),
            lifecycle_event_id="LC-F2",
            physical_event_id="PH-F2",
        )
    store.close()


def test_revision_outcomes_cursor_pages_without_duplicates_or_gaps(tmp_path) -> None:
    database = tmp_path / "paging.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        cursor = None
        seen = []
        snapshot_versions = set()
        while True:
            page = session.knowledge.revision_outcomes_page(
                "PART-PAGE",
                limit=2,
                cursor=cursor,
            )
            seen.extend(item.revision_id for item in page.items)
            snapshot_versions.add(page.snapshot_version)
            cursor = page.next_cursor
            if cursor is None:
                break

        assert seen == ["R1", "R2", "R3", "R4", "R5"]
        assert len(seen) == len(set(seen))
        assert snapshot_versions == {session.snapshot_version}


def test_equipment_history_cursor_is_bound_to_filter_set(tmp_path) -> None:
    database = tmp_path / "filters.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.equipment_position_history_page(
            equipment_id="EQ-PAGE",
            position="LEFT",
            limit=2,
        )
        assert len(first.items) == 2
        assert first.next_cursor is not None

        second = session.knowledge.equipment_position_history_page(
            equipment_id="EQ-PAGE",
            position="LEFT",
            limit=2,
            cursor=first.next_cursor,
        )
        assert second.items
        assert set(item.event_id for item in first.items).isdisjoint(
            item.event_id for item in second.items
        )

        with pytest.raises(
            LifecycleKnowledgeCursorError,
            match="different query or filter set",
        ):
            session.knowledge.equipment_position_history_page(
                equipment_id="EQ-PAGE",
                position="LEFT",
                event_type="FAILED",
                limit=2,
                cursor=first.next_cursor,
            )


def test_cursor_is_rejected_after_database_advances_to_new_snapshot(tmp_path) -> None:
    database = tmp_path / "stale.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.revision_outcomes_page("PART-PAGE", limit=2)
        old_cursor = first.next_cursor
        old_version = session.snapshot_version
    assert old_cursor is not None

    writer = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(writer)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                "R6",
                "PART-PAGE",
                "REV06",
                T0 + timedelta(days=1),
                parent_revision_id="R5",
            ),
            event_id="LC-R6",
        )
    assert writer.loaded_version == old_version + 1
    writer.close()

    with SQLiteLifecycleReadOnlySession(database) as fresh:
        assert fresh.snapshot_version == old_version + 1
        with pytest.raises(LifecycleKnowledgeCursorError, match="snapshot is stale"):
            fresh.knowledge.revision_outcomes_page(
                "PART-PAGE",
                limit=2,
                cursor=old_cursor,
            )


def test_tampered_cursor_and_invalid_limits_fail_closed(tmp_path) -> None:
    database = tmp_path / "tamper.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.revision_outcomes_page("PART-PAGE", limit=2)
        assert first.next_cursor is not None
        cursor = first.next_cursor
        replacement = "A" if cursor[-1] != "A" else "B"
        tampered = cursor[:-1] + replacement

        with pytest.raises(LifecycleKnowledgeCursorError):
            session.knowledge.revision_outcomes_page(
                "PART-PAGE",
                limit=2,
                cursor=tampered,
            )
        with pytest.raises(LifecycleKnowledgeCursorError, match="between 1 and 500"):
            session.knowledge.revision_outcomes_page("PART-PAGE", limit=0)
        with pytest.raises(LifecycleKnowledgeCursorError, match="between 1 and 500"):
            session.knowledge.revision_outcomes_page("PART-PAGE", limit=501)


def test_failure_pattern_pages_and_legacy_queries_remain_consistent(tmp_path) -> None:
    database = tmp_path / "patterns.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.failure_patterns_page(
            part_id="PART-PAGE",
            limit=1,
        )
        assert len(first.items) == 1
        assert first.next_cursor is not None
        second = session.knowledge.failure_patterns_page(
            part_id="PART-PAGE",
            limit=1,
            cursor=first.next_cursor,
        )
        assert len(second.items) == 1
        assert second.next_cursor is None
        paged = first.items + second.items
        assert paged == session.knowledge.failure_patterns(part_id="PART-PAGE")

        legacy_outcomes = session.knowledge.revision_outcomes("PART-PAGE")
        assert [item.revision_id for item in legacy_outcomes] == [
            "R1",
            "R2",
            "R3",
            "R4",
            "R5",
        ]
