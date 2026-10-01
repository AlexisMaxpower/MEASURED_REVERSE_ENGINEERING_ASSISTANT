from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import (
    LifecycleReadOnlyStaleError,
    LifecycleUnitOfWork,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
)


T0 = datetime(2026, 10, 1, 2, 30, tzinfo=timezone.utc)


def _seed_one_revision(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-GUARD", "REV01", T0),
            event_id="LC-R1",
        )
    store.close()


def _append_second_revision(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                "R2",
                "PART-GUARD",
                "REV02",
                T0 + timedelta(minutes=1),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
    store.close()


def test_open_read_only_session_rejects_external_snapshot_drift(tmp_path) -> None:
    database = tmp_path / "snapshot-guard.db"
    _seed_one_revision(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        initial_version = session.snapshot_version
        assert [
            item.revision_id
            for item in session.queries.revision_history("PART-GUARD")
        ] == ["R1"]
        assert [
            item.revision_id
            for item in session.knowledge.revision_outcomes("PART-GUARD")
        ] == ["R1"]

        # A completed read must not leave a long-lived SQLite read transaction that
        # blocks the writer. The external commit advances both authoritative and
        # relational/materialized generations atomically.
        _append_second_revision(database)

        with pytest.raises(
            LifecycleReadOnlyStaleError,
            match="snapshot changed; refresh required",
        ):
            session.queries.revision_history("PART-GUARD")

        with pytest.raises(
            LifecycleReadOnlyStaleError,
            match="snapshot changed; refresh required",
        ):
            session.knowledge.revision_outcomes("PART-GUARD")

        assert session.snapshot_version == initial_version
        assert session.refresh() == initial_version + 1
        assert [
            item.revision_id
            for item in session.queries.revision_history("PART-GUARD")
        ] == ["R1", "R2"]
        assert [
            item.revision_id
            for item in session.knowledge.revision_outcomes("PART-GUARD")
        ] == ["R1", "R2"]
