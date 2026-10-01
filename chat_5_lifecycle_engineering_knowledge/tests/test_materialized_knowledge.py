from datetime import datetime, timedelta, timezone
import sqlite3

from mrea_lifecycle import (
    FailureRecord,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    Revision,
    SQLiteKeysetEngineeringKnowledgeRepository,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    SQLiteMaterializedEngineeringKnowledgeRepository,
)
from mrea_lifecycle.knowledge_paging import (
    encode_knowledge_cursor,
    query_fingerprint,
)


T0 = datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc)


def _seed(database) -> None:
    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-MAT", "REV01", T0),
            event_id="LC-R1",
        )
        uow.revisions.create(
            Revision(
                "R2",
                "PART-MAT",
                "REV02",
                T0 + timedelta(hours=1),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                "M1",
                "R1",
                "PETG",
                "FDM",
                T0 + timedelta(hours=2),
            ),
            event_id="LC-M1",
        )
        for record, event_id in (
            (
                FailureRecord(
                    "F1",
                    "R1",
                    T0 + timedelta(hours=3),
                    "CRACK",
                    "HINGE",
                    "service",
                    ("EV-F1",),
                    confirmed_cause="FATIGUE",
                ),
                "LC-F1",
            ),
            (
                FailureRecord(
                    "F2",
                    "R1",
                    T0 + timedelta(hours=4),
                    "CRACK",
                    "HINGE",
                    "service",
                    ("EV-F2",),
                    confirmed_cause="FATIGUE",
                ),
                "LC-F2",
            ),
            (
                FailureRecord(
                    "F3",
                    "R2",
                    T0 + timedelta(hours=5),
                    "CRACK",
                    "HINGE",
                    "service",
                    ("EV-F3",),
                    confirmed_cause="FATIGUE",
                ),
                "LC-F3",
            ),
            (
                FailureRecord(
                    "F4",
                    "R2",
                    T0 + timedelta(hours=6),
                    "WEAR",
                    "PIN",
                    "service",
                    ("EV-F4",),
                    confirmed_cause=None,
                ),
                "LC-F4",
            ),
        ):
            uow.failures.record(record, event_id=event_id)
    assert store.loaded_version == store.read_model_version == 1
    store.close()


def test_materialized_tables_are_snapshot_synchronized_and_match_raw_semantics(
    tmp_path,
) -> None:
    database = tmp_path / "materialized.db"
    _seed(database)

    connection = sqlite3.connect(database)
    try:
        revision_rows = connection.execute(
            """
            SELECT revision_id, manufacturing_records, failure_records
            FROM lifecycle_revision_outcomes_materialized
            ORDER BY revision_id
            """
        ).fetchall()
        pattern_rows = connection.execute(
            """
            SELECT scope_type, scope_id, failure_type, occurrence_count,
                   revision_count, instance_count
            FROM lifecycle_failure_patterns_materialized
            ORDER BY scope_type, scope_id, occurrence_count DESC, failure_type
            """
        ).fetchall()
    finally:
        connection.close()

    assert revision_rows == [("R1", 1, 2), ("R2", 0, 2)]
    assert ("GLOBAL", "*", "CRACK", 3, 2, 0) in pattern_rows
    assert ("PART", "PART-MAT", "CRACK", 3, 2, 0) in pattern_rows
    assert ("REVISION", "R1", "CRACK", 2, 1, 0) in pattern_rows
    assert ("REVISION", "R2", "WEAR", 1, 1, 0) in pattern_rows

    with SQLiteLifecycleReadOnlySession(database) as session:
        assert isinstance(
            session.knowledge,
            SQLiteMaterializedEngineeringKnowledgeRepository,
        )
        assert session._connection is not None
        raw = SQLiteKeysetEngineeringKnowledgeRepository(
            session._connection,
            snapshot_version=session.snapshot_version,
        )
        assert session.knowledge.revision_outcomes("PART-MAT") == raw.revision_outcomes(
            "PART-MAT"
        )
        assert session.knowledge.failure_patterns(
            part_id="PART-MAT"
        ) == raw.failure_patterns(part_id="PART-MAT")
        assert session.knowledge.failure_patterns(
            part_id="PART-MAT", revision_id="R2"
        ) == raw.failure_patterns(part_id="PART-MAT", revision_id="R2")


def test_new_v2_reads_use_materialized_tables_without_raw_aggregate_scan(tmp_path) -> None:
    database = tmp_path / "materialized-query.db"
    _seed(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        assert session._connection is not None
        statements: list[str] = []
        session._connection.set_trace_callback(statements.append)
        try:
            revision_page = session.knowledge.revision_outcomes_page(
                "PART-MAT", limit=1
            )
            failure_page = session.knowledge.failure_patterns_page(
                part_id="PART-MAT", limit=1
            )
        finally:
            session._connection.set_trace_callback(None)

    assert revision_page.next_cursor is not None
    assert failure_page.next_cursor is not None
    sql = "\n".join(statements).upper()
    assert "LIFECYCLE_REVISION_OUTCOMES_MATERIALIZED" in sql
    assert "LIFECYCLE_FAILURE_PATTERNS_MATERIALIZED" in sql
    assert "COUNT(DISTINCT" not in sql
    assert "FROM LIFECYCLE_FAILURES AS F" not in sql


def test_legacy_failure_cursor_keeps_historical_raw_offset_path(tmp_path) -> None:
    database = tmp_path / "legacy-cursor.db"
    _seed(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        fingerprint = query_fingerprint(
            "failure_patterns_page",
            {"part_id": "PART-MAT", "revision_id": None},
        )
        legacy = encode_knowledge_cursor(
            query_fingerprint_value=fingerprint,
            snapshot_version=session.snapshot_version,
            offset=1,
        )
        assert session._connection is not None
        statements: list[str] = []
        session._connection.set_trace_callback(statements.append)
        try:
            page = session.knowledge.failure_patterns_page(
                part_id="PART-MAT",
                limit=1,
                cursor=legacy,
            )
        finally:
            session._connection.set_trace_callback(None)

    assert [item.failure_type for item in page.items] == ["WEAR"]
    sql = "\n".join(statements).upper()
    assert "FROM LIFECYCLE_FAILURES AS F" in sql
    assert "OFFSET 1" in sql


def test_materialized_projection_refreshes_atomically_on_next_commit(tmp_path) -> None:
    database = tmp_path / "refresh.db"
    _seed(database)

    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.failures.record(
            FailureRecord(
                "F5",
                "R2",
                T0 + timedelta(hours=7),
                "CRACK",
                "HINGE",
                "service",
                ("EV-F5",),
                confirmed_cause="FATIGUE",
            ),
            event_id="LC-F5",
        )
    assert store.loaded_version == store.read_model_version == 2
    store.close()

    with SQLiteLifecycleReadOnlySession(database) as session:
        revision = {
            item.revision_id: item
            for item in session.knowledge.revision_outcomes("PART-MAT")
        }
        patterns = session.knowledge.failure_patterns(part_id="PART-MAT")

    assert revision["R2"].failure_records == 3
    crack = next(item for item in patterns if item.failure_type == "CRACK")
    assert crack.occurrence_count == 4
    assert crack.revision_count == 2
