from datetime import datetime, timedelta, timezone
import json
import sqlite3
from urllib.parse import urlencode

from mrea_lifecycle import (
    Installation,
    LIFECYCLE_HTTP_API_SCHEMA_VERSION,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalTestOutcome,
    Revision,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
    build_read_only_lifecycle_http_app,
)


T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)
ROUTE = "/v1/lifecycle/physical-field-status"


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-FIELD-HTTP", "REV01", T0),
            event_id="LC-R1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                "M1",
                "R1",
                "PETG",
                "FDM",
                T0 + timedelta(minutes=1),
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
                "EQ-1",
                "LEFT",
                T0 + timedelta(hours=1),
                instance_id="PI-1",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T1",
                "R1",
                T0 + timedelta(hours=2),
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
            activated_at=T0 + timedelta(hours=3),
            physical_event_id="PH-A1",
            notes="released to service",
        )
    store.close()


def _request(app, method: str, path: str, query: str = ""):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    chunks = app(
        {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
        },
        start_response,
    )
    body = b"".join(chunks)
    return (
        int(captured["status"].split()[0]),
        captured["headers"],
        json.loads(body.decode("utf-8")),
        body,
    )


def test_physical_field_status_http_projects_exact_committed_source_event(tmp_path) -> None:
    database = tmp_path / "field-status-http.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)
    query = urlencode({"instance_id": "PI-1"})

    first = _request(app, "GET", ROUTE, query)
    second = _request(app, "GET", ROUTE, query)

    assert first[0] == second[0] == 200
    assert first[3] == second[3]

    payload = first[2]
    assert payload["schema_version"] == LIFECYCLE_HTTP_API_SCHEMA_VERSION
    assert payload["snapshot_version"] >= 1
    assert payload["data"] == {
        "equipment_id": "EQ-1",
        "failure_id": None,
        "installation_id": "I1",
        "instance_id": "PI-1",
        "manufacturing_id": "M1",
        "notes": "released to service",
        "position": "LEFT",
        "replacement_instance_id": None,
        "revision_id": "R1",
        "source_event_id": "PH-A1",
        "source_event_sequence": 4,
        "state": "ACTIVE",
        "state_changed_at": (T0 + timedelta(hours=3)).isoformat(),
        "test_id": "T1",
        "test_outcome": None,
    }


def test_physical_field_status_http_rejects_invalid_requests_fail_closed(tmp_path) -> None:
    database = tmp_path / "field-status-http-invalid.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, _, missing, _ = _request(app, "GET", ROUTE)
    assert status == 400
    assert missing["error"]["code"] == "invalid_request"
    assert "instance_id" in missing["error"]["message"]

    status, _, unknown, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode({"instance_id": "UNKNOWN"}),
    )
    assert status == 400
    assert unknown["error"]["code"] == "invalid_request"
    assert "does not exist" in unknown["error"]["message"]

    status, _, unexpected, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode({"instance_id": "PI-1", "infer": "true"}),
    )
    assert status == 400
    assert unexpected["error"]["code"] == "invalid_request"
    assert "unexpected query parameter" in unexpected["error"]["message"]

    status, headers, method_error, _ = _request(app, "POST", ROUTE)
    assert status == 405
    assert headers["Allow"] == "GET"
    assert method_error["error"]["code"] == "method_not_allowed"


def test_physical_field_status_http_returns_conflict_for_corrupt_durable_timeline(tmp_path) -> None:
    database = tmp_path / "field-status-http-corrupt.db"
    _seed_database(database)

    connection = sqlite3.connect(database)
    try:
        connection.execute(
            """
            UPDATE lifecycle_physical_events_relational
            SET event_type = 'ACTIVATED'
            WHERE event_id = 'PH-I1'
            """
        )
        connection.commit()
    finally:
        connection.close()

    app = build_read_only_lifecycle_http_app(database)
    status, _, payload, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode({"instance_id": "PI-1"}),
    )

    assert status == 409
    assert payload["error"]["code"] == "read_model_integrity_error"
    assert "impossible transition" in payload["error"]["message"]


def test_pass19_adapter_preserves_existing_routes(tmp_path) -> None:
    database = tmp_path / "field-status-http-delegation.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, _, payload, _ = _request(
        app,
        "GET",
        "/v1/lifecycle/physical-timeline",
        urlencode({"instance_id": "PI-1"}),
    )

    assert status == 200
    assert payload["data"][-1]["event_id"] == "PH-A1"
    assert payload["data"][-1]["event_type"] == "ACTIVATED"
