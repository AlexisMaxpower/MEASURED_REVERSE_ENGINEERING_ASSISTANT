import sqlite3

import pytest

from mrea_lifecycle import (
    LifecycleKnowledgeCursorError,
    SQLiteKeysetEngineeringKnowledgeRepository,
)
from mrea_lifecycle.knowledge_paging import (
    KnowledgeKeysetCursorState,
    decode_knowledge_keyset_cursor,
    encode_knowledge_cursor,
    encode_knowledge_keyset_cursor,
    query_fingerprint,
)


SNAPSHOT_VERSION = 7


def _repository() -> tuple[
    sqlite3.Connection,
    SQLiteKeysetEngineeringKnowledgeRepository,
]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE lifecycle_revisions (
            revision_id TEXT PRIMARY KEY,
            part_id TEXT NOT NULL
        );
        CREATE TABLE lifecycle_failures (
            failure_id TEXT PRIMARY KEY,
            revision_id TEXT NOT NULL,
            instance_id TEXT NOT NULL,
            failure_type TEXT NOT NULL,
            damage_location TEXT NOT NULL,
            confirmed_cause TEXT,
            failed_at TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        "INSERT INTO lifecycle_revisions(revision_id, part_id) VALUES (?, ?)",
        (("R1", "PART-PATTERN"), ("R2", "PART-PATTERN")),
    )
    rows = (
        ("F1", "R1", "I1", "CRACK", "HINGE", "FATIGUE", "2026-09-01T10:00:00+00:00"),
        ("F2", "R1", "I2", "CRACK", "HINGE", "FATIGUE", "2026-09-02T10:00:00+00:00"),
        ("F3", "R2", "I3", "CRACK", "HINGE", "FATIGUE", "2026-09-03T10:00:00+00:00"),
        ("F4", "R1", "I4", "DEFORMATION", "MOUNT", "OVERLOAD", "2026-09-04T10:00:00+00:00"),
        ("F5", "R2", "I5", "DEFORMATION", "MOUNT", "OVERLOAD", "2026-09-05T10:00:00+00:00"),
        ("F6", "R1", "I6", "WEAR", "PIN", None, "2026-09-06T10:00:00+00:00"),
        ("F7", "R1", "I7", "WEAR", "PIN", "", "2026-09-07T10:00:00+00:00"),
        ("F8", "R2", "I8", "WEAR", "PIN", "ABRASION", "2026-09-08T10:00:00+00:00"),
    )
    connection.executemany(
        """
        INSERT INTO lifecycle_failures(
            failure_id, revision_id, instance_id, failure_type,
            damage_location, confirmed_cause, failed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return (
        connection,
        SQLiteKeysetEngineeringKnowledgeRepository(
            connection,
            snapshot_version=SNAPSHOT_VERSION,
        ),
    )


def _signature(item) -> tuple[object, ...]:
    return (
        item.failure_type,
        item.damage_location,
        item.confirmed_cause,
        item.occurrence_count,
    )


def test_failure_patterns_emit_v2_and_traverse_grouped_results_without_gaps() -> None:
    connection, repository = _repository()
    try:
        first = repository.failure_patterns_page(
            part_id="PART-PATTERN",
            limit=2,
        )
        assert [_signature(item) for item in first.items] == [
            ("CRACK", "HINGE", "FATIGUE", 3),
            ("DEFORMATION", "MOUNT", "OVERLOAD", 2),
        ]
        assert first.next_cursor is not None

        fingerprint = query_fingerprint(
            "failure_patterns_page",
            {"part_id": "PART-PATTERN", "revision_id": None},
        )
        state = decode_knowledge_keyset_cursor(
            first.next_cursor,
            expected_query_fingerprint=fingerprint,
            expected_snapshot_version=SNAPSHOT_VERSION,
        )
        assert isinstance(state, KnowledgeKeysetCursorState)
        assert state.key == (2, "DEFORMATION", "MOUNT", 1, "OVERLOAD")

        seen = list(first.items)
        cursor = first.next_cursor
        while cursor is not None:
            page = repository.failure_patterns_page(
                part_id="PART-PATTERN",
                limit=2,
                cursor=cursor,
            )
            seen.extend(page.items)
            cursor = page.next_cursor

        assert [_signature(item) for item in seen] == [
            ("CRACK", "HINGE", "FATIGUE", 3),
            ("DEFORMATION", "MOUNT", "OVERLOAD", 2),
            ("WEAR", "PIN", None, 1),
            ("WEAR", "PIN", "", 1),
            ("WEAR", "PIN", "ABRASION", 1),
        ]
        assert len({_signature(item) for item in seen}) == 5
    finally:
        connection.close()


def test_failure_pattern_v2_continuation_uses_key_predicates_without_offset() -> None:
    connection, repository = _repository()
    try:
        first = repository.failure_patterns_page(
            part_id="PART-PATTERN",
            limit=2,
        )
        assert first.next_cursor is not None
        statements: list[str] = []
        connection.set_trace_callback(statements.append)
        try:
            second = repository.failure_patterns_page(
                part_id="PART-PATTERN",
                limit=2,
                cursor=first.next_cursor,
            )
        finally:
            connection.set_trace_callback(None)

        assert [_signature(item) for item in second.items] == [
            ("WEAR", "PIN", None, 1),
            ("WEAR", "PIN", "", 1),
        ]
        select_sql = "\n".join(
            statement.upper()
            for statement in statements
            if "WITH PATTERNS AS" in statement.upper()
        )
        assert "OFFSET" not in select_sql
        assert "OCCURRENCE_COUNT <" in select_sql
        assert "CAUSE_NULL_RANK >" in select_sql
        assert "CAUSE_SORT >" in select_sql
    finally:
        connection.close()


def test_failure_pattern_legacy_v1_cursor_remains_on_offset_path() -> None:
    connection, repository = _repository()
    try:
        fingerprint = query_fingerprint(
            "failure_patterns_page",
            {"part_id": "PART-PATTERN", "revision_id": None},
        )
        legacy = encode_knowledge_cursor(
            query_fingerprint_value=fingerprint,
            snapshot_version=SNAPSHOT_VERSION,
            offset=1,
        )
        statements: list[str] = []
        connection.set_trace_callback(statements.append)
        try:
            page = repository.failure_patterns_page(
                part_id="PART-PATTERN",
                limit=1,
                cursor=legacy,
            )
        finally:
            connection.set_trace_callback(None)

        assert [_signature(item) for item in page.items] == [
            ("DEFORMATION", "MOUNT", "OVERLOAD", 2),
        ]
        assert page.next_cursor is not None
        select_sql = "\n".join(
            statement.upper()
            for statement in statements
            if "LIFECYCLE_FAILURES" in statement.upper()
        )
        assert "OFFSET 1" in select_sql
    finally:
        connection.close()


def test_failure_pattern_keyset_shape_fails_closed() -> None:
    connection, repository = _repository()
    try:
        fingerprint = query_fingerprint(
            "failure_patterns_page",
            {"part_id": "PART-PATTERN", "revision_id": None},
        )
        malformed = encode_knowledge_keyset_cursor(
            query_fingerprint_value=fingerprint,
            snapshot_version=SNAPSHOT_VERSION,
            key=(1, "WEAR"),
        )
        with pytest.raises(
            LifecycleKnowledgeCursorError,
            match="invalid failure-pattern keyset cursor",
        ):
            repository.failure_patterns_page(
                part_id="PART-PATTERN",
                limit=2,
                cursor=malformed,
            )
    finally:
        connection.close()
