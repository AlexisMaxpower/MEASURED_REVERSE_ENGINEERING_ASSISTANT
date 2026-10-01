from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from mrea_lifecycle import (
    FailureRecord,
    LifecycleState,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
)
from mrea_lifecycle.revision_explanation import explain_revision_changes


T0 = datetime(2026, 10, 2, 6, 0, tzinfo=timezone.utc)


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-EXPLAIN",
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
                part_id="PART-EXPLAIN",
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


def _fact_map(explanation):
    return {(fact.category, fact.field): fact for fact in explanation.facts}


def test_revision_change_explanation_is_deterministic_and_evidence_backed(tmp_path) -> None:
    database = tmp_path / "revision-change-explanation.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        explanation = explain_revision_changes(session.knowledge, "R1", "R2")

    assert explanation.part_id == "PART-EXPLAIN"
    assert explanation.left_revision_id == "R1"
    assert explanation.right_revision_id == "R2"
    assert explanation.changed_categories == (
        "revision_metadata",
        "materials",
        "manufacturing_methods",
        "manufacturing_records",
        "tests",
        "failures",
        "lifecycle_state",
    )

    facts = _fact_map(explanation)
    assert facts[("revision_metadata", "parent_revision_id")].left_value is None
    assert facts[("revision_metadata", "parent_revision_id")].right_value == "R1"
    assert facts[("revision_metadata", "notes")].left_value == "thin hinge"
    assert facts[("revision_metadata", "notes")].right_value == "reinforced hinge"

    materials = facts[("materials", "materials")]
    assert materials.left_value == ("PETG",)
    assert materials.right_value == ("PA12",)
    assert materials.left_source.record_ids == ("M1",)
    assert materials.right_source.record_ids == ("M2",)

    tests = facts[("tests", "tests")]
    assert tests.left_source.record_ids == ("T1",)
    assert tests.right_source.record_ids == ("T2",)
    assert tests.left_source.artifact_ids == ("TEST-PHOTO-1",)
    assert tests.right_source.artifact_ids == ("TEST-PHOTO-2",)

    failures = facts[("failures", "failures")]
    assert failures.left_source.record_ids == ("F1",)
    assert failures.left_source.artifact_ids == ("FAIL-PHOTO-1", "FAIL-PHOTO-2")
    assert failures.right_source.record_ids == ()
    assert failures.right_source.artifact_ids == ()

    state = facts[("lifecycle_state", "state")]
    assert state.left_value is LifecycleState.FAILED
    assert state.right_value is LifecycleState.ACTIVE

    assert all("geometry" not in fact.category for fact in explanation.facts)
    assert all("geometry" not in fact.field for fact in explanation.facts)


def test_revision_change_explanation_has_no_fabricated_delta_for_same_revision(tmp_path) -> None:
    database = tmp_path / "revision-change-explanation-same.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        explanation = explain_revision_changes(session.knowledge, "R2", "R2")

    assert explanation.changed_categories == ()
    assert explanation.facts == ()


def test_revision_change_explanation_preserves_fail_closed_comparison_validation(tmp_path) -> None:
    database = tmp_path / "revision-change-explanation-invalid.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        with pytest.raises(ValueError, match="both revisions must exist"):
            explain_revision_changes(session.knowledge, "R1", "UNKNOWN")
        with pytest.raises(ValueError, match="different parts"):
            explain_revision_changes(session.knowledge, "R1", "R3")
