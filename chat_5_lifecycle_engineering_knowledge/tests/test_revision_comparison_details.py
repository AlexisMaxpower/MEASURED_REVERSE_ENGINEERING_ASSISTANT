from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from urllib.parse import urlencode

import pytest

from mrea_lifecycle import (
    FailureRecord,
    LIFECYCLE_HTTP_API_SCHEMA_VERSION,
    LifecycleState,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
    build_read_only_lifecycle_http_app,
)


T0 = datetime(2026, 10, 1, 4, 30, tzinfo=timezone.utc)


def _seed_detail_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-DETAIL",
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
                part_id="PART-DETAIL",
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
                print_profile="0.20-strength",
                contractor="internal",
                cost=Decimal("12.50"),
                post_processing="deburr",
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


def test_detailed_revision_comparison_exposes_exact_structured_facts(tmp_path) -> None:
    database = tmp_path / "revision-comparison-details.db"
    _seed_detail_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        details = session.knowledge.compare_revision_details("R1", "R2")

    assert details.left.revision_code == "REV01"
    assert details.left.notes == "thin hinge"
    assert details.left.source_cad_artifact_id == "CAD-R1"
    assert details.left.materials == ("PETG",)
    assert details.left.manufacturing_methods == ("FDM",)
    assert details.left.manufacturing[0].batch == "B1"
    assert details.left.manufacturing[0].machine == "P1"
    assert details.left.manufacturing[0].cost == "12.50"
    assert details.left.tests[0].artifact_ids == ("TEST-PHOTO-1",)
    assert details.left.failures[0].confirmed_cause == "stress concentration"
    assert details.left.failures[0].evidence_artifact_ids == (
        "FAIL-PHOTO-1",
        "FAIL-PHOTO-2",
    )
    assert details.left.state is LifecycleState.FAILED

    assert details.right.parent_revision_id == "R1"
    assert details.right.materials == ("PA12",)
    assert details.right.manufacturing_methods == ("SLS",)
    assert details.right.tests[0].result == "pass"
    assert details.right.failures == ()
    assert details.right.state is LifecycleState.ACTIVE

    assert details.changed_categories == (
        "revision_metadata",
        "materials",
        "manufacturing_methods",
        "manufacturing_records",
        "tests",
        "failures",
        "lifecycle_state",
    )


def test_detailed_revision_comparison_rejects_missing_and_cross_part_inputs(tmp_path) -> None:
    database = tmp_path / "revision-comparison-details-invalid.db"
    _seed_detail_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        with pytest.raises(ValueError, match="both revisions must exist"):
            session.knowledge.compare_revision_details("R1", "UNKNOWN")
        with pytest.raises(ValueError, match="different parts"):
            session.knowledge.compare_revision_details("R1", "R3")


def test_detailed_revision_comparison_is_exposed_over_existing_get_only_http_boundary(
    tmp_path,
) -> None:
    database = tmp_path / "revision-comparison-details-http.db"
    _seed_detail_database(database)
    app = build_read_only_lifecycle_http_app(database)

    response = app.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison-details",
        raw_query=urlencode(
            {"left_revision_id": "R1", "right_revision_id": "R2"}
        ),
    )
    payload = json.loads(response.body)

    assert response.status == 200
    assert payload["schema_version"] == LIFECYCLE_HTTP_API_SCHEMA_VERSION
    assert payload["snapshot_version"] > 0
    data = payload["data"]
    assert data["left"]["revision_code"] == "REV01"
    assert data["left"]["manufacturing"][0]["material"] == "PETG"
    assert data["left"]["tests"][0]["artifact_ids"] == ["TEST-PHOTO-1"]
    assert data["left"]["failures"][0]["evidence_artifact_ids"] == [
        "FAIL-PHOTO-1",
        "FAIL-PHOTO-2",
    ]
    assert data["right"]["state"] == "ACTIVE"
    assert data["changed_categories"] == [
        "revision_metadata",
        "materials",
        "manufacturing_methods",
        "manufacturing_records",
        "tests",
        "failures",
        "lifecycle_state",
    ]
    assert "geometry" not in data


def test_detailed_revision_comparison_http_fails_closed_on_invalid_requests(tmp_path) -> None:
    database = tmp_path / "revision-comparison-details-http-invalid.db"
    _seed_detail_database(database)
    app = build_read_only_lifecycle_http_app(database)

    missing = app.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison-details",
        raw_query="left_revision_id=R1",
    )
    cross_part = app.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison-details",
        raw_query="left_revision_id=R1&right_revision_id=R3",
    )
    unexpected = app.dispatch(
        method="GET",
        path="/v1/knowledge/revision-comparison-details",
        raw_query="left_revision_id=R1&right_revision_id=R2&rank=true",
    )

    assert missing.status == 400
    assert cross_part.status == 400
    assert unexpected.status == 400
    assert json.loads(unexpected.body)["error"]["code"] == "invalid_request"
