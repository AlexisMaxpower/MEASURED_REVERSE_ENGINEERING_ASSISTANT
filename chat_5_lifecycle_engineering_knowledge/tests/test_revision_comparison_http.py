import json
from datetime import datetime, timedelta, timezone

from mrea_lifecycle import (
    ManufacturingRecord,
    ReadOnlyLifecycleHttpAPI,
    Revision,
    SQLiteLifecycleStore,
    LifecycleUnitOfWork,
)


T0 = datetime(2026, 10, 1, 3, 30, tzinfo=timezone.utc)


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-HTTP-CMP", "REV01", T0), event_id="LC-R1"
        )
        uow.revisions.create(
            Revision(
                "R2",
                "PART-HTTP-CMP",
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
            ManufacturingRecord("M2", "R2", "ABS", "FDM", T0 + timedelta(hours=4)),
            event_id="LC-M2",
        )
    store.close()


def test_revision_comparison_http_returns_snapshot_bound_facts(tmp_path) -> None:
    database = tmp_path / "revision-comparison-http.db"
    _seed_database(database)
    api = ReadOnlyLifecycleHttpAPI(database)

    response = api.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison",
        raw_query="left_revision_id=R1&right_revision_id=R2",
    )

    assert response.status == 200
    payload = json.loads(response.body)
    assert payload["schema_version"] == "mrea.lifecycle-http.v1"
    assert payload["snapshot_version"] >= 1
    assert payload["data"] == {
        "left_failure_count": 0,
        "left_materials": ["PETG"],
        "left_revision_id": "R1",
        "left_state": "MANUFACTURED",
        "left_test_count": 0,
        "right_failure_count": 0,
        "right_materials": ["ABS"],
        "right_revision_id": "R2",
        "right_state": "MANUFACTURED",
        "right_test_count": 0,
    }


def test_revision_comparison_http_rejects_invalid_inputs(tmp_path) -> None:
    database = tmp_path / "revision-comparison-http-invalid.db"
    _seed_database(database)
    api = ReadOnlyLifecycleHttpAPI(database)

    missing = api.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison",
        raw_query="left_revision_id=R1",
    )
    assert missing.status == 400
    assert json.loads(missing.body)["error"]["code"] == "invalid_request"

    cross_part = api.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison",
        raw_query="left_revision_id=R1&right_revision_id=R3",
    )
    assert cross_part.status == 400
    assert json.loads(cross_part.body)["error"]["code"] == "invalid_request"

    unexpected = api.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison",
        raw_query="left_revision_id=R1&right_revision_id=R2&cursor=x",
    )
    assert unexpected.status == 400
    assert json.loads(unexpected.body)["error"]["code"] == "invalid_request"
