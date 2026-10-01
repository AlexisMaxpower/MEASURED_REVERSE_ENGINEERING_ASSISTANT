from datetime import datetime, timezone

import pytest

from mrea_lifecycle import (
    CADRuntimeStatus,
    LifecycleInvariantError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    SQLiteLifecycleStore,
)


NOW = datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc)


def _cad_package(*, adapter: str = "SOLIDWORKS_2026") -> dict[str, object]:
    return {
        "schema_version": "mrea.cad-package.v1",
        "cad_package_id": "CAD-R4-001",
        "sketch_package_id": "SP-R4-001",
        "adapter": adapter,
        "artifacts": [],
    }


def _verification_report(*, status: str = "VERIFIED") -> dict[str, object]:
    return {
        "schema_version": "mrea.cad-verification.v1",
        "report_id": "CADV-R4-001",
        "cad_package_id": "CAD-R4-001",
        "sketch_package_id": "SP-R4-001",
        "overall_status": status,
    }


def _runtime_evidence(
    *,
    status: str,
    real_host_executed: bool,
    adapter: str = "SOLIDWORKS_2026",
) -> dict[str, object]:
    return {
        "schema_version": "mrea.cad-runtime-evidence.v1",
        "status": status,
        "adapter_name": adapter,
        "real_host_executed": real_host_executed,
        "sketch_package_id": "SP-R4-001",
        "cad_package_id": "CAD-R4-001",
    }


def _prepare(
    store: SQLiteLifecycleStore,
    *,
    revision_id: str,
    verification_status: str = "VERIFIED",
    runtime_status: str | None = "UNVERIFIED",
    real_host_executed: bool = False,
):
    uow = LifecycleUnitOfWork(store)
    kwargs: dict[str, object] = {}
    if runtime_status is not None:
        kwargs["runtime_evidence"] = _runtime_evidence(
            status=runtime_status,
            real_host_executed=real_host_executed,
        )
    with uow.transaction():
        revision = uow.cad_revisions.prepare(
            revision_id=revision_id,
            part_id="PART-R4",
            revision_code=revision_id,
            created_at=NOW,
            cad_package=_cad_package(),
            verification_report=_verification_report(status=verification_status),
            event_id=f"EV-{revision_id}",
            **kwargs,
        )
    return uow, revision


def test_numerically_verified_runtime_unverified_is_ineligible_and_persists(
    tmp_path,
) -> None:
    database = tmp_path / "runtime-unverified.db"
    store = SQLiteLifecycleStore(database)
    uow, revision = _prepare(store, revision_id="REV-R4-UNVERIFIED")

    assert revision.cad_link is not None
    assert revision.cad_link.runtime_status is CADRuntimeStatus.UNVERIFIED
    assert revision.cad_link.runtime_evidence_schema_version == (
        "mrea.cad-runtime-evidence.v1"
    )
    assert revision.cad_link.runtime_real_host_executed is False
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is False

    with pytest.raises(LifecycleInvariantError, match="runtime|not VERIFIED"):
        with uow.transaction():
            uow.manufacturing.record(
                ManufacturingRecord(
                    manufacturing_id="MFG-BLOCKED",
                    revision_id=revision.revision_id,
                    material="PETG",
                    method="FDM",
                    manufactured_at=NOW,
                ),
                event_id="EV-MFG-BLOCKED",
            )

    row = store.queries.revision_history("PART-R4")[0]
    assert row.verification_status == "VERIFIED"
    assert row.runtime_status == "UNVERIFIED"
    assert row.runtime_evidence_schema_version == "mrea.cad-runtime-evidence.v1"
    assert row.runtime_real_host_executed is False
    assert "MFG-BLOCKED" not in store.manufacturing_records
    store.close()

    reopened = SQLiteLifecycleStore(database)
    reopened_revision = reopened.revisions[revision.revision_id]
    assert reopened_revision.cad_link is not None
    assert reopened_revision.cad_link.runtime_status is CADRuntimeStatus.UNVERIFIED
    assert reopened_revision.cad_link.runtime_real_host_executed is False
    assert (
        LifecycleUnitOfWork(reopened).manufacturing.is_revision_eligible(
            revision.revision_id
        )
        is False
    )
    reopened_row = reopened.queries.revision_history("PART-R4")[0]
    assert reopened_row.runtime_status == "UNVERIFIED"
    reopened.close()


def test_numerical_failure_remains_ineligible_with_runtime_unverified(tmp_path) -> None:
    store = SQLiteLifecycleStore(tmp_path / "runtime-mismatch.db")
    uow, revision = _prepare(
        store,
        revision_id="REV-R4-MISMATCH",
        verification_status="FAILED",
        runtime_status="UNVERIFIED",
    )
    assert revision.cad_link is not None
    assert revision.cad_link.runtime_status is CADRuntimeStatus.UNVERIFIED
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is False
    store.close()


@pytest.mark.parametrize("runtime_status", ["FAILED", "UNVERIFIED"])
def test_runtime_non_verified_states_fail_closed(tmp_path, runtime_status: str) -> None:
    store = SQLiteLifecycleStore(tmp_path / f"runtime-{runtime_status.lower()}.db")
    uow, revision = _prepare(
        store,
        revision_id=f"REV-{runtime_status}",
        runtime_status=runtime_status,
        real_host_executed=True,
    )
    assert revision.cad_link is not None
    assert revision.cad_link.runtime_status is CADRuntimeStatus(runtime_status)
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is False
    store.close()


def test_explicit_runtime_verified_with_real_host_is_eligible(tmp_path) -> None:
    store = SQLiteLifecycleStore(tmp_path / "runtime-verified.db")
    uow, revision = _prepare(
        store,
        revision_id="REV-RUNTIME-VERIFIED",
        runtime_status="VERIFIED",
        real_host_executed=True,
    )
    assert revision.cad_link is not None
    assert revision.cad_link.runtime_status is CADRuntimeStatus.VERIFIED
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is True
    store.close()


def test_runtime_verified_without_real_host_is_rejected(tmp_path) -> None:
    store = SQLiteLifecycleStore(tmp_path / "runtime-invalid-verified.db")
    uow = LifecycleUnitOfWork(store)
    with pytest.raises(
        LifecycleInvariantError,
        match="VERIFIED requires real_host_executed=true",
    ):
        with uow.transaction():
            uow.cad_revisions.prepare(
                revision_id="REV-RUNTIME-INVALID",
                part_id="PART-R4",
                revision_code="REV-RUNTIME-INVALID",
                created_at=NOW,
                cad_package=_cad_package(),
                verification_report=_verification_report(),
                runtime_evidence=_runtime_evidence(
                    status="VERIFIED",
                    real_host_executed=False,
                ),
                event_id="EV-RUNTIME-INVALID",
            )
    assert store.revisions == {}
    store.close()


def test_generic_verified_path_without_runtime_evidence_remains_compatible(
    tmp_path,
) -> None:
    store = SQLiteLifecycleStore(tmp_path / "generic-compatible.db")
    uow, revision = _prepare(
        store,
        revision_id="REV-GENERIC",
        runtime_status=None,
    )
    assert revision.cad_link is not None
    assert revision.cad_link.runtime_status is None
    assert revision.cad_link.runtime_evidence_schema_version is None
    assert revision.cad_link.runtime_real_host_executed is None
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is True

    with uow.transaction():
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="MFG-GENERIC",
                revision_id=revision.revision_id,
                material="PETG",
                method="FDM",
                manufactured_at=NOW,
            ),
            event_id="EV-MFG-GENERIC",
        )
    assert "MFG-GENERIC" in store.manufacturing_records
    row = store.queries.revision_history("PART-R4")[0]
    assert row.runtime_status is None
    store.close()
