from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from mrea_lifecycle import (
    CADArtifactReference,
    CADRevisionLink,
    CADVerificationStatus,
    CanonicalLifecycleEventAdapter,
    InMemoryLifecycleStore,
    Installation,
    LifecycleConcurrencyError,
    LifecycleTransactionRequiredError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    PhysicalPartState,
    PhysicalPartStateProjection,
    PhysicalTestOutcome,
    Revision,
    RevisionOrigin,
    RevisionService,
    SQLiteLifecycleStore,
    TestRecord as LifecycleTestRecord,
)


T0 = datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc)


def _verified_cad_revision() -> Revision:
    return Revision(
        revision_id="R1",
        part_id="PART-0042",
        revision_code="REV01",
        created_at=T0,
        origin=RevisionOrigin.CAD_TRANSFER,
        cad_link=CADRevisionLink(
            cad_package_id="CAD-001",
            sketch_package_id="SP-001",
            cad_verification_report_id="VR-001",
            cad_adapter="solidworks-2026",
            verification_status=CADVerificationStatus.VERIFIED,
            artifacts=(
                CADArtifactReference(
                    artifact_id="ART-CAD-001",
                    kind="SOLIDWORKS_NATIVE",
                    uri="artifact://cad/part.SLDPRT",
                    sha256="abc123",
                    metadata={"role": "native", "revision": 1},
                ),
            ),
        ),
    )


def test_sqlite_roundtrip_preserves_cad_and_physical_lifecycle(tmp_path) -> None:
    database = tmp_path / "lifecycle.db"
    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)

    with uow.transaction():
        uow.revisions.create(_verified_cad_revision(), event_id="LC-R1")
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M1",
                revision_id="R1",
                material="PETG",
                method="FDM",
                manufactured_at=T0 + timedelta(hours=1),
                machine="Printer-A",
                batch="BATCH-01",
                cost=Decimal("12.50"),
            ),
            event_id="LC-M1",
        )
        uow.physical.register_manufactured(
            instance_id="PI-001",
            manufacturing_id="M1",
            physical_event_id="PH-M1",
        )
        uow.physical.install(
            Installation(
                installation_id="I1",
                revision_id="R1",
                manufacturing_id="M1",
                equipment_id="FREEZER-01",
                position="INNER_DOOR_LEFT",
                installed_at=T0 + timedelta(hours=2),
                instance_id="PI-001",
            ),
            lifecycle_event_id="LC-I1",
            physical_event_id="PH-I1",
        )
        uow.physical.test(
            LifecycleTestRecord(
                test_id="T1",
                revision_id="R1",
                manufacturing_id="M1",
                installation_id="I1",
                instance_id="PI-001",
                tested_at=T0 + timedelta(hours=3),
                test_type="FIT_AND_LOAD",
                conditions="installed on target equipment",
                result="pass",
                conclusion="accepted",
                artifact_ids=("ART-TEST-001",),
            ),
            outcome=PhysicalTestOutcome.PASSED,
            lifecycle_event_id="LC-T1",
            physical_event_id="PH-T1",
        )
        uow.physical.activate(
            instance_id="PI-001",
            activated_at=T0 + timedelta(hours=4),
            physical_event_id="PH-ACTIVE-1",
        )

    assert store.loaded_version == 1
    store.close()

    reopened = SQLiteLifecycleStore(database)
    assert reopened.loaded_version == 1
    assert reopened.revisions["R1"].origin is RevisionOrigin.CAD_TRANSFER
    assert reopened.revisions["R1"].cad_link is not None
    assert reopened.revisions["R1"].cad_link.artifacts[0].metadata == {
        "role": "native",
        "revision": 1,
    }
    assert reopened.manufacturing_records["M1"].cost == Decimal("12.50")
    assert reopened.tests["T1"].artifact_ids == ("ART-TEST-001",)
    assert PhysicalPartStateProjection(reopened).for_instance("PI-001") is PhysicalPartState.ACTIVE

    canonical = CanonicalLifecycleEventAdapter().export(reopened.events)
    assert [event["event_type"] for event in canonical] == [
        "REVISION_CREATED",
        "MANUFACTURED",
        "INSTALLED",
        "TESTED",
    ]
    assert all("instance_id" not in event for event in canonical)
    reopened.close()


def test_unit_of_work_rolls_back_canonical_and_physical_writes_together(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "atomic.db"
    store = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(store)

    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-0042",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-R1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M1",
                revision_id="R1",
                material="PETG",
                method="FDM",
                manufactured_at=T0 + timedelta(hours=1),
            ),
            event_id="LC-M1",
        )
        uow.physical.register_manufactured(
            instance_id="PI-001",
            manufacturing_id="M1",
            physical_event_id="PH-M1",
        )

    assert store.loaded_version == 1

    def explode(**kwargs):
        raise RuntimeError("forced physical append failure")

    monkeypatch.setattr(store, "append_physical_event", explode)

    with pytest.raises(RuntimeError, match="forced physical append failure"):
        with uow.transaction():
            uow.physical.install(
                Installation(
                    installation_id="I1",
                    revision_id="R1",
                    manufacturing_id="M1",
                    equipment_id="FREEZER-01",
                    position="INNER_DOOR_LEFT",
                    installed_at=T0 + timedelta(hours=2),
                    instance_id="PI-001",
                ),
                lifecycle_event_id="LC-I1",
                physical_event_id="PH-I1",
            )

    assert store.loaded_version == 1
    assert "I1" not in store.installations
    assert all(event.installation_id != "I1" for event in store.events)
    store.close()

    reopened = SQLiteLifecycleStore(database)
    assert reopened.loaded_version == 1
    assert "I1" not in reopened.installations
    assert all(event.installation_id != "I1" for event in reopened.events)
    assert PhysicalPartStateProjection(reopened).for_instance("PI-001") is PhysicalPartState.MANUFACTURED
    reopened.close()


def test_stale_sqlite_writer_is_rejected_until_reload(tmp_path) -> None:
    database = tmp_path / "concurrency.db"
    first = SQLiteLifecycleStore(database)
    second = SQLiteLifecycleStore(database)
    first_uow = LifecycleUnitOfWork(first)
    second_uow = LifecycleUnitOfWork(second)

    assert first.loaded_version == second.loaded_version == 0

    with first_uow.transaction():
        first_uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-0042",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-R1",
        )

    assert first.loaded_version == 1
    assert second.loaded_version == 0

    with pytest.raises(LifecycleConcurrencyError, match="stale lifecycle repository"):
        with second_uow.transaction():
            pass

    assert second.revisions == {}
    second.reload()
    assert second.loaded_version == 1
    assert "R1" in second.revisions

    with second_uow.transaction():
        second_uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M1",
                revision_id="R1",
                material="PETG",
                method="FDM",
                manufactured_at=T0 + timedelta(hours=1),
            ),
            event_id="LC-M1",
        )

    assert second.loaded_version == 2
    first.reload()
    assert first.loaded_version == 2
    assert "M1" in first.manufacturing_records
    first.close()
    second.close()


def test_sqlite_mutation_without_unit_of_work_fails_closed(tmp_path) -> None:
    database = tmp_path / "required-uow.db"
    store = SQLiteLifecycleStore(database)

    with pytest.raises(
        LifecycleTransactionRequiredError,
        match="LifecycleUnitOfWork.transaction",
    ):
        RevisionService(store).create(
            Revision(
                revision_id="R-UNSAFE",
                part_id="PART-0042",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-UNSAFE",
        )

    assert store.revisions == {}
    assert store.events == []
    assert store.loaded_version == 0
    store.close()

    reopened = SQLiteLifecycleStore(database)
    assert reopened.revisions == {}
    assert reopened.events == []
    assert reopened.loaded_version == 0
    reopened.close()


def test_in_memory_transaction_restores_state_on_error() -> None:
    store = InMemoryLifecycleStore()

    with pytest.raises(RuntimeError, match="abort"):
        with store.transaction():
            RevisionService(store).create(
                Revision(
                    revision_id="R1",
                    part_id="PART-0042",
                    revision_code="REV01",
                    created_at=T0,
                ),
                event_id="LC-R1",
            )
            raise RuntimeError("abort")

    assert store.revisions == {}
    assert store.events == []
    assert store.transaction_depth == 0
