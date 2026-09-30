from datetime import datetime, timedelta, timezone

from mrea_lifecycle import (
    Installation,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalTestOutcome,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
)
from mrea_lifecycle.knowledge_paging import (
    KnowledgeKeysetCursorState,
    decode_knowledge_keyset_cursor,
    encode_knowledge_cursor,
    query_fingerprint,
)


T0 = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def _seed_revisions(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        previous = None
        for index in range(1, 7):
            revision_id = f"R{index}"
            uow.revisions.create(
                Revision(
                    revision_id,
                    "PART-KEYSET",
                    f"REV{index:02d}",
                    T0 + timedelta(minutes=index),
                    parent_revision_id=previous,
                ),
                event_id=f"LC-{revision_id}",
            )
            previous = revision_id
    store.close()


def _seed_equipment_history(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-EQ", "REV01", T0),
            event_id="LC-R1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                "M1",
                "R1",
                "PETG",
                "FDM",
                T0 + timedelta(hours=1),
            ),
            event_id="LC-M1",
        )
        uow.physical.register_manufactured(
            instance_id="PI-1",
            manufacturing_id="M1",
            physical_event_id="PH-M1",
        )
        uow.physical.install(
            Installation(
                "I1",
                "R1",
                "M1",
                "EQ-KEYSET",
                "LEFT",
                T0 + timedelta(hours=2),
                instance_id="PI-1",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T1",
                "R1",
                T0 + timedelta(hours=3),
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
            activated_at=T0 + timedelta(hours=4),
            physical_event_id="PH-A1",
        )
    store.close()


def test_revision_outcomes_emit_v2_keyset_and_traverse_without_gaps(tmp_path) -> None:
    database = tmp_path / "revisions.db"
    _seed_revisions(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.revision_outcomes_page(
            "PART-KEYSET",
            limit=2,
        )
        assert [item.revision_id for item in first.items] == ["R1", "R2"]
        assert first.next_cursor is not None

        fingerprint = query_fingerprint(
            "revision_outcomes_page",
            {"part_id": "PART-KEYSET"},
        )
        state = decode_knowledge_keyset_cursor(
            first.next_cursor,
            expected_query_fingerprint=fingerprint,
            expected_snapshot_version=session.snapshot_version,
        )
        assert isinstance(state, KnowledgeKeysetCursorState)
        assert state.key[1] == "R2"

        seen = list(first.items)
        cursor = first.next_cursor
        while cursor is not None:
            page = session.knowledge.revision_outcomes_page(
                "PART-KEYSET",
                limit=2,
                cursor=cursor,
            )
            seen.extend(page.items)
            cursor = page.next_cursor

        assert [item.revision_id for item in seen] == [
            "R1",
            "R2",
            "R3",
            "R4",
            "R5",
            "R6",
        ]
        assert len({item.revision_id for item in seen}) == 6


def test_keyset_continuation_sql_does_not_use_offset(tmp_path) -> None:
    database = tmp_path / "trace.db"
    _seed_revisions(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.revision_outcomes_page(
            "PART-KEYSET",
            limit=2,
        )
        assert first.next_cursor is not None
        statements: list[str] = []
        assert session._connection is not None
        session._connection.set_trace_callback(statements.append)
        try:
            second = session.knowledge.revision_outcomes_page(
                "PART-KEYSET",
                limit=2,
                cursor=first.next_cursor,
            )
        finally:
            session._connection.set_trace_callback(None)

        assert [item.revision_id for item in second.items] == ["R3", "R4"]
        select_sql = "\n".join(
            statement.upper()
            for statement in statements
            if "LIFECYCLE_REVISIONS" in statement.upper()
        )
        assert "OFFSET" not in select_sql
        assert "R.CREATED_AT >" in select_sql
        assert "R.REVISION_ID >" in select_sql


def test_legacy_v1_offset_cursor_remains_accepted(tmp_path) -> None:
    database = tmp_path / "legacy.db"
    _seed_revisions(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        fingerprint = query_fingerprint(
            "revision_outcomes_page",
            {"part_id": "PART-KEYSET"},
        )
        legacy = encode_knowledge_cursor(
            query_fingerprint_value=fingerprint,
            snapshot_version=session.snapshot_version,
            offset=2,
        )
        page = session.knowledge.revision_outcomes_page(
            "PART-KEYSET",
            limit=2,
            cursor=legacy,
        )
        assert [item.revision_id for item in page.items] == ["R3", "R4"]
        assert page.next_cursor is not None


def test_equipment_history_uses_three_part_keyset(tmp_path) -> None:
    database = tmp_path / "equipment.db"
    _seed_equipment_history(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = session.knowledge.equipment_position_history_page(
            equipment_id="EQ-KEYSET",
            position="LEFT",
            limit=2,
        )
        assert [item.event_type for item in first.items] == ["INSTALLED", "TESTED"]
        assert first.next_cursor is not None

        fingerprint = query_fingerprint(
            "equipment_position_history_page",
            {
                "equipment_id": "EQ-KEYSET",
                "position": "LEFT",
                "event_type": None,
                "revision_id": None,
                "instance_id": None,
            },
        )
        state = decode_knowledge_keyset_cursor(
            first.next_cursor,
            expected_query_fingerprint=fingerprint,
            expected_snapshot_version=session.snapshot_version,
        )
        assert isinstance(state, KnowledgeKeysetCursorState)
        assert len(state.key) == 3
        assert state.key[2] == first.items[-1].event_id

        second = session.knowledge.equipment_position_history_page(
            equipment_id="EQ-KEYSET",
            position="LEFT",
            limit=2,
            cursor=first.next_cursor,
        )
        assert [item.event_type for item in second.items] == ["ACTIVATED"]
        assert second.next_cursor is None
