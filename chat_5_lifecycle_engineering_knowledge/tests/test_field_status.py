from datetime import datetime, timedelta, timezone

import pytest

from mrea_lifecycle import (
    FailureRecord,
    Installation,
    LifecycleKnowledgeIntegrityError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalPartState,
    PhysicalTestOutcome,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
    build_physical_field_status,
    get_physical_field_status,
)
from mrea_lifecycle.relational import PhysicalEventQueryResult


T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision("R1", "PART-FIELD", "REV01", T0),
            event_id="LC-R1",
        )

        for index, suffix in enumerate(("A", "F", "R"), start=1):
            manufacturing_id = f"M-{suffix}"
            instance_id = f"PI-{suffix}"
            installation_id = f"I-{suffix}"
            test_id = f"T-{suffix}"
            manufactured_at = T0 + timedelta(minutes=index)
            installed_at = T0 + timedelta(hours=1, minutes=index)
            tested_at = T0 + timedelta(hours=2, minutes=index)
            activated_at = T0 + timedelta(hours=3, minutes=index)

            uow.manufacturing.record(
                ManufacturingRecord(
                    manufacturing_id,
                    "R1",
                    "PETG",
                    "FDM",
                    manufactured_at,
                ),
                event_id=f"LC-M-{suffix}",
            )
            uow.physical.register_manufactured(
                instance_id=instance_id,
                manufacturing_id=manufacturing_id,
                physical_event_id=f"PH-M-{suffix}",
            )
            uow.physical.install(
                Installation(
                    installation_id,
                    "R1",
                    manufacturing_id,
                    "EQ-FIELD",
                    suffix,
                    installed_at,
                    instance_id=instance_id,
                ),
                lifecycle_event_id=f"LC-I-{suffix}",
                physical_event_id=f"PH-I-{suffix}",
            )
            uow.physical.test(
                LifecycleTestRecord(
                    test_id,
                    "R1",
                    tested_at,
                    "LOAD",
                    "nominal",
                    "pass",
                    "accepted",
                    manufacturing_id=manufacturing_id,
                    installation_id=installation_id,
                    instance_id=instance_id,
                ),
                outcome=PhysicalTestOutcome.PASSED,
                lifecycle_event_id=f"LC-T-{suffix}",
                physical_event_id=f"PH-T-{suffix}",
            )
            uow.physical.activate(
                instance_id=instance_id,
                activated_at=activated_at,
                physical_event_id=f"PH-A-{suffix}",
                notes=f"activated {suffix}",
            )

        uow.physical.fail(
            FailureRecord(
                "F-F",
                "R1",
                T0 + timedelta(hours=4, minutes=2),
                "CRACK",
                "HINGE",
                "service load",
                ("FAIL-EVIDENCE-F",),
                manufacturing_id="M-F",
                installation_id="I-F",
                instance_id="PI-F",
            ),
            lifecycle_event_id="LC-F-F",
            physical_event_id="PH-F-F",
        )

        uow.physical.fail(
            FailureRecord(
                "F-R",
                "R1",
                T0 + timedelta(hours=4, minutes=3),
                "CRACK",
                "HINGE",
                "service load",
                ("FAIL-EVIDENCE-R",),
                manufacturing_id="M-R",
                installation_id="I-R",
                instance_id="PI-R",
            ),
            lifecycle_event_id="LC-F-R",
            physical_event_id="PH-F-R",
        )
        uow.physical.remove(
            instance_id="PI-R",
            removed_at=T0 + timedelta(hours=5, minutes=3),
            physical_event_id="PH-RM-R",
            reason="removed for replacement",
        )
    store.close()


def test_field_status_projects_latest_committed_state_and_exact_source_event(tmp_path) -> None:
    database = tmp_path / "field-status.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        active = get_physical_field_status(session.queries, "PI-A")
        failed = get_physical_field_status(session.queries, "PI-F")
        removed = get_physical_field_status(session.queries, "PI-R")

    assert active.state is PhysicalPartState.ACTIVE
    assert active.source_event_id == "PH-A-A"
    assert active.installation_id == "I-A"
    assert active.test_id == "T-A"
    assert active.failure_id is None
    assert active.equipment_id == "EQ-FIELD"
    assert active.position == "A"
    assert active.notes == "activated A"

    assert failed.state is PhysicalPartState.FAILED
    assert failed.source_event_id == "PH-F-F"
    assert failed.failure_id == "F-F"
    assert failed.equipment_id == "EQ-FIELD"
    assert failed.position == "F"

    assert removed.state is PhysicalPartState.REMOVED
    assert removed.source_event_id == "PH-RM-R"
    assert removed.equipment_id == "EQ-FIELD"
    assert removed.position == "R"
    assert removed.notes == "removed for replacement"


def test_field_status_is_deterministic_for_same_snapshot(tmp_path) -> None:
    database = tmp_path / "field-status-deterministic.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        first = get_physical_field_status(session.queries, "PI-F")
        second = get_physical_field_status(session.queries, "PI-F")

    assert first == second


def test_field_status_rejects_missing_or_blank_instance(tmp_path) -> None:
    database = tmp_path / "field-status-missing.db"
    _seed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        with pytest.raises(ValueError, match="non-empty string"):
            get_physical_field_status(session.queries, "")
        with pytest.raises(ValueError, match="does not exist or has no lifecycle events"):
            get_physical_field_status(session.queries, "UNKNOWN")


def _event(
    *,
    event_id: str,
    event_type: str,
    sequence: int,
    occurred_at: datetime,
    instance_id: str = "PI-X",
    revision_id: str = "R-X",
    manufacturing_id: str = "M-X",
) -> PhysicalEventQueryResult:
    return PhysicalEventQueryResult(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        sequence=sequence,
        instance_id=instance_id,
        revision_id=revision_id,
        manufacturing_id=manufacturing_id,
        installation_id=None,
        test_id=None,
        failure_id=None,
        equipment_id=None,
        position=None,
        test_outcome=None,
        replacement_instance_id=None,
        notes=None,
    )


def test_field_status_fails_closed_on_corrupt_timeline_identity_or_order() -> None:
    first = _event(
        event_id="PH-1",
        event_type="MANUFACTURED",
        sequence=1,
        occurred_at=T0,
    )

    with pytest.raises(LifecycleKnowledgeIntegrityError, match="multiple instance"):
        build_physical_field_status(
            (
                first,
                _event(
                    event_id="PH-2",
                    event_type="INSTALLED",
                    sequence=2,
                    occurred_at=T0 + timedelta(minutes=1),
                    instance_id="PI-OTHER",
                ),
            )
        )

    with pytest.raises(LifecycleKnowledgeIntegrityError, match="strictly increasing"):
        build_physical_field_status(
            (
                first,
                _event(
                    event_id="PH-2",
                    event_type="INSTALLED",
                    sequence=1,
                    occurred_at=T0 + timedelta(minutes=1),
                ),
            )
        )

    with pytest.raises(LifecycleKnowledgeIntegrityError, match="backward in time"):
        build_physical_field_status(
            (
                first,
                _event(
                    event_id="PH-2",
                    event_type="INSTALLED",
                    sequence=2,
                    occurred_at=T0 - timedelta(minutes=1),
                ),
            )
        )


def test_field_status_fails_closed_on_unknown_event_type() -> None:
    with pytest.raises(LifecycleKnowledgeIntegrityError, match="unsupported physical"):
        build_physical_field_status(
            (
                _event(
                    event_id="PH-X",
                    event_type="UNKNOWN",
                    sequence=1,
                    occurred_at=T0,
                ),
            )
        )
