from datetime import datetime, timedelta, timezone
import json
import sqlite3
from urllib.parse import urlencode

from mrea_lifecycle import (
    FailureRecord,
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


T0 = datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc)


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-HTTP", "REV01", T0),
            event_id="LC-R1",
        )
        uow.revisions.create(
            Revision(
                "R2",
                "PART-HTTP",
                "REV02",
                T0 + timedelta(minutes=1),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                "M1", "R1", "PETG", "FDM", T0 + timedelta(hours=1)
            ),
            event_id="LC-M1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                "M2", "R2", "PETG", "FDM", T0 + timedelta(hours=2)
            ),
            event_id="LC-M2",
        )
        uow.physical.register_manufactured(
            instance_id="PI-1",
            manufacturing_id="M1",
            physical_event_id="PH-M1",
        )
        uow.physical.register_manufactured(
            instance_id="PI-2",
            manufacturing_id="M2",
            physical_event_id="PH-M2",
        )
        uow.physical.install(
            Installation(
                "I1",
                "R1",
                "M1",
                "EQ-HTTP",
                "LEFT",
                T0 + timedelta(hours=3),
                instance_id="PI-1",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T1",
                "R1",
                T0 + timedelta(hours=4),
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
            activated_at=T0 + timedelta(hours=5),
            physical_event_id="PH-A1",
        )
        uow.physical.fail(
            FailureRecord(
                "F1",
                "R1",
                T0 + timedelta(hours=6),
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
            removed_at=T0 + timedelta(hours=7),
            physical_event_id="PH-RM1",
            reason="replacement",
        )
        uow.physical.install(
            Installation(
                "I2",
                "R2",
                "M2",
                "EQ-HTTP",
                "LEFT",
                T0 + timedelta(hours=8),
                instance_id="PI-2",
            ),
            lifecycle_event_id="LC-I2",
            physical_event_id="PH-I2",
        )
        uow.physical.test(
            LifecycleTestRecord(
                "T2",
                "R2",
                T0 + timedelta(hours=9),
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
            activated_at=T0 + timedelta(hours=10),
            physical_event_id="PH-A2",
        )
        uow.physical.supersede(
            instance_id="PI-1",
            replacement_instance_id="PI-2",
            superseded_at=T0 + timedelta(hours=11),
            physical_event_id="PH-S1",
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


def test_health_reports_verified_read_only_snapshot(tmp_path) -> None:
    database = tmp_path / "http.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, headers, payload, _ = _request(app, "GET", "/health")

    assert status == 200
    assert payload["schema_version"] == LIFECYCLE_HTTP_API_SCHEMA_VERSION
    assert payload["snapshot_version"] >= 1
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["read_only"] is True
    assert payload["data"]["read_model_version"] == payload["snapshot_version"]
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_all_read_only_routes_expose_committed_facts(tmp_path) -> None:
    database = tmp_path / "routes.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    requests = (
        ("/v1/lifecycle/revisions", {"part_id": "PART-HTTP"}),
        ("/v1/lifecycle/failures", {"instance_id": "PI-1"}),
        ("/v1/lifecycle/equipment-occupancy", {"equipment_id": "EQ-HTTP"}),
        ("/v1/lifecycle/physical-timeline", {"instance_id": "PI-1"}),
        ("/v1/knowledge/revision-lineage", {"part_id": "PART-HTTP"}),
        ("/v1/knowledge/revision-outcomes", {"part_id": "PART-HTTP"}),
        ("/v1/knowledge/equipment-history", {"equipment_id": "EQ-HTTP"}),
        ("/v1/knowledge/failure-patterns", {"part_id": "PART-HTTP"}),
        ("/v1/knowledge/replacement-chain", {"instance_id": "PI-1"}),
    )

    payloads = {}
    for path, params in requests:
        status, _, payload, _ = _request(app, "GET", path, urlencode(params))
        assert status == 200, (path, payload)
        assert payload["schema_version"] == LIFECYCLE_HTTP_API_SCHEMA_VERSION
        assert payload["snapshot_version"] >= 1
        payloads[path] = payload["data"]

    assert [item["revision_id"] for item in payloads["/v1/lifecycle/revisions"]] == [
        "R1",
        "R2",
    ]
    assert payloads["/v1/lifecycle/failures"][0]["failure_id"] == "F1"
    assert payloads["/v1/lifecycle/equipment-occupancy"][0]["instance_id"] == "PI-2"
    assert payloads["/v1/lifecycle/physical-timeline"][-1]["event_type"] == "SUPERSEDED"
    assert [item["depth"] for item in payloads["/v1/knowledge/revision-lineage"]] == [0, 1]
    assert [
        item["revision_id"]
        for item in payloads["/v1/knowledge/revision-outcomes"]["items"]
    ] == ["R1", "R2"]
    assert payloads["/v1/knowledge/equipment-history"]["items"]
    assert payloads["/v1/knowledge/failure-patterns"]["items"][0]["confirmed_cause"] == "FATIGUE"
    assert [
        item["instance_id"]
        for item in payloads["/v1/knowledge/replacement-chain"]
    ] == ["PI-1", "PI-2"]


def test_pagination_cursor_round_trips_and_remains_query_bound(tmp_path) -> None:
    database = tmp_path / "paging-http.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, _, first, _ = _request(
        app,
        "GET",
        "/v1/knowledge/revision-outcomes",
        urlencode({"part_id": "PART-HTTP", "limit": 1}),
    )
    assert status == 200
    assert first["data"]["items"][0]["revision_id"] == "R1"
    cursor = first["data"]["next_cursor"]
    assert cursor is not None

    status, _, second, _ = _request(
        app,
        "GET",
        "/v1/knowledge/revision-outcomes",
        urlencode({"part_id": "PART-HTTP", "limit": 1, "cursor": cursor}),
    )
    assert status == 200
    assert second["data"]["items"][0]["revision_id"] == "R2"
    assert second["data"]["next_cursor"] is None

    status, _, mismatch, _ = _request(
        app,
        "GET",
        "/v1/knowledge/revision-outcomes",
        urlencode({"part_id": "OTHER", "limit": 1, "cursor": cursor}),
    )
    assert status == 400
    assert mismatch["error"]["code"] == "invalid_request"
    assert "different query or filter set" in mismatch["error"]["message"]


def test_http_contract_rejects_writes_duplicates_and_unknown_inputs(tmp_path) -> None:
    database = tmp_path / "reject.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    _, _, before, _ = _request(app, "GET", "/health")
    before_version = before["snapshot_version"]

    status, headers, payload, _ = _request(app, "POST", "/v1/lifecycle/revisions")
    assert status == 405
    assert headers["Allow"] == "GET"
    assert payload["error"]["code"] == "method_not_allowed"

    status, _, duplicate, _ = _request(
        app,
        "GET",
        "/v1/lifecycle/revisions",
        "part_id=PART-HTTP&part_id=OTHER",
    )
    assert status == 400
    assert "must appear once" in duplicate["error"]["message"]

    status, _, unexpected, _ = _request(
        app,
        "GET",
        "/v1/lifecycle/revisions",
        "part_id=PART-HTTP&write=true",
    )
    assert status == 400
    assert "unexpected query parameter" in unexpected["error"]["message"]

    status, _, missing_route, _ = _request(app, "GET", "/v1/not-a-route")
    assert status == 404
    assert missing_route["error"]["code"] == "route_not_found"

    _, _, after, _ = _request(app, "GET", "/health")
    assert after["snapshot_version"] == before_version


def test_stale_read_model_and_missing_database_fail_closed(tmp_path) -> None:
    database = tmp_path / "stale-http.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE lifecycle_read_model_meta SET snapshot_version = snapshot_version - 1 WHERE singleton = 1"
        )
        connection.commit()

    status, _, stale, _ = _request(app, "GET", "/health")
    assert status == 409
    assert stale["error"]["code"] == "read_model_stale"

    missing = build_read_only_lifecycle_http_app(tmp_path / "missing.db")
    status, _, unavailable, _ = _request(missing, "GET", "/health")
    assert status == 503
    assert unavailable["error"]["code"] == "read_model_unavailable"


def test_json_response_is_deterministic_for_same_snapshot(tmp_path) -> None:
    database = tmp_path / "deterministic-http.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)
    query = urlencode({"part_id": "PART-HTTP"})

    first = _request(app, "GET", "/v1/lifecycle/revisions", query)
    second = _request(app, "GET", "/v1/lifecycle/revisions", query)

    assert first[0] == second[0] == 200
    assert first[3] == second[3]
