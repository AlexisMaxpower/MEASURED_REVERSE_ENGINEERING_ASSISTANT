from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from urllib.parse import urlencode

from mrea_lifecycle import (
    FailureRecord,
    LIFECYCLE_HTTP_API_SCHEMA_VERSION,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    Revision,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
    build_read_only_lifecycle_http_app,
)


T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)
ROUTE = "/v1/knowledge/revision-change-explanation"


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-EXPLAIN-HTTP",
                revision_code="REV01",
                created_at=T0,
                notes="thin hinge",
                source_cad_artifact_id="CAD-R1",
            ),
            event_id="LC-R1",
        )
        uow.revisions.create(
            Revision(
                revision_id="R2",
                part_id="PART-EXPLAIN-HTTP",
                revision_code="REV02",
                created_at=T0 + timedelta(minutes=1),
                parent_revision_id="R1",
                notes="reinforced hinge",
                source_cad_artifact_id="CAD-R2",
            ),
            event_id="LC-R2",
        )
        uow.revisions.create(
            Revision(
                revision_id="R3",
                part_id="OTHER-PART",
                revision_code="REV01",
                created_at=T0 + timedelta(minutes=2),
            ),
            event_id="LC-R3",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M1",
                revision_id="R1",
                material="PETG",
                method="FDM",
                manufactured_at=T0 + timedelta(hours=1),
                batch="B1",
                machine="P1",
                cost=Decimal("12.50"),
            ),
            event_id="LC-M1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M2",
                revision_id="R2",
                material="PA12",
                method="SLS",
                manufactured_at=T0 + timedelta(hours=2),
                batch="B2",
                contractor="supplier-a",
                cost=Decimal("42.00"),
            ),
            event_id="LC-M2",
        )
        uow.tests.record(
            LifecycleTestRecord(
                test_id="T1",
                revision_id="R1",
                tested_at=T0 + timedelta(hours=3),
                test_type="LOAD",
                conditions="fixture A / 100 N",
                result="fail",
                conclusion="crack observed",
                manufacturing_id="M1",
                artifact_ids=("TEST-PHOTO-1",),
            ),
            event_id="LC-T1",
        )
        uow.failures.record(
            FailureRecord(
                failure_id="F1",
                revision_id="R1",
                failed_at=T0 + timedelta(hours=4),
                failure_type="CRACK",
                damage_location="HINGE-H2",
                circumstances="service load",
                evidence_artifact_ids=("FAIL-PHOTO-1", "FAIL-PHOTO-2"),
                manufacturing_id="M1",
                estimated_cause="fatigue",
                confirmed_cause="stress concentration",
                related_feature="H2",
            ),
            event_id="LC-F1",
        )
        uow.tests.record(
            LifecycleTestRecord(
                test_id="T2",
                revision_id="R2",
                tested_at=T0 + timedelta(hours=5),
                test_type="LOAD",
                conditions="fixture A / 100 N",
                result="pass",
                conclusion="accepted",
                manufacturing_id="M2",
                artifact_ids=("TEST-PHOTO-2",),
            ),
            event_id="LC-T2",
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


def _fact_map(payload):
    return {
        (fact["category"], fact["field"]): fact
        for fact in payload["data"]["facts"]
    }


def test_revision_change_explanation_http_is_source_backed_and_deterministic(tmp_path) -> None:
    database = tmp_path / "revision-change-explanation-http.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)
    query = urlencode({"left_revision_id": "R1", "right_revision_id": "R2"})

    first = _request(app, "GET", ROUTE, query)
    second = _request(app, "GET", ROUTE, query)

    assert first[0] == second[0] == 200
    assert first[3] == second[3]

    payload = first[2]
    assert payload["schema_version"] == LIFECYCLE_HTTP_API_SCHEMA_VERSION
    assert payload["snapshot_version"] >= 1
    assert payload["data"]["part_id"] == "PART-EXPLAIN-HTTP"
    assert payload["data"]["left_revision_id"] == "R1"
    assert payload["data"]["right_revision_id"] == "R2"
    assert payload["data"]["changed_categories"] == [
        "revision_metadata",
        "materials",
        "manufacturing_methods",
        "manufacturing_records",
        "tests",
        "failures",
        "lifecycle_state",
    ]

    facts = _fact_map(payload)
    assert facts[("materials", "materials")]["left_source"]["record_ids"] == ["M1"]
    assert facts[("materials", "materials")]["right_source"]["record_ids"] == ["M2"]
    assert facts[("tests", "tests")]["left_source"]["record_ids"] == ["T1"]
    assert facts[("tests", "tests")]["right_source"]["record_ids"] == ["T2"]
    assert facts[("tests", "tests")]["left_source"]["artifact_ids"] == ["TEST-PHOTO-1"]
    assert facts[("tests", "tests")]["right_source"]["artifact_ids"] == ["TEST-PHOTO-2"]
    assert facts[("failures", "failures")]["left_source"]["record_ids"] == ["F1"]
    assert facts[("failures", "failures")]["left_source"]["artifact_ids"] == [
        "FAIL-PHOTO-1",
        "FAIL-PHOTO-2",
    ]
    assert facts[("failures", "failures")]["right_source"]["record_ids"] == []
    assert facts[("lifecycle_state", "state")]["left_value"] == "FAILED"
    assert facts[("lifecycle_state", "state")]["right_value"] == "ACTIVE"

    serialized = first[3].decode("utf-8").lower()
    assert "geometry" not in serialized
    assert "recommendation" not in serialized
    assert "ranking" not in serialized


def test_revision_change_explanation_http_same_revision_has_no_fabricated_delta(tmp_path) -> None:
    database = tmp_path / "revision-change-explanation-http-same.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, _, payload, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode({"left_revision_id": "R2", "right_revision_id": "R2"}),
    )

    assert status == 200
    assert payload["data"]["changed_categories"] == []
    assert payload["data"]["facts"] == []


def test_revision_change_explanation_http_rejects_invalid_inputs_fail_closed(tmp_path) -> None:
    database = tmp_path / "revision-change-explanation-http-invalid.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, _, missing, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode({"left_revision_id": "R1"}),
    )
    assert status == 400
    assert missing["error"]["code"] == "invalid_request"
    assert "right_revision_id" in missing["error"]["message"]

    status, _, cross_part, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode({"left_revision_id": "R1", "right_revision_id": "R3"}),
    )
    assert status == 400
    assert cross_part["error"]["code"] == "invalid_request"
    assert "different parts" in cross_part["error"]["message"]

    status, _, unexpected, _ = _request(
        app,
        "GET",
        ROUTE,
        urlencode(
            {
                "left_revision_id": "R1",
                "right_revision_id": "R2",
                "recommend": "true",
            }
        ),
    )
    assert status == 400
    assert unexpected["error"]["code"] == "invalid_request"
    assert "unexpected query parameter" in unexpected["error"]["message"]

    status, headers, method_error, _ = _request(app, "POST", ROUTE)
    assert status == 405
    assert headers["Allow"] == "GET"
    assert method_error["error"]["code"] == "method_not_allowed"
