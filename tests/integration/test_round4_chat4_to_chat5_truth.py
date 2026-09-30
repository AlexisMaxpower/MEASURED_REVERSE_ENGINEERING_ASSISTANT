from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mrea_cad_bridge import TestDoubleCadAdapter, execute_cad_runtime_validation_v1
from mrea_lifecycle import (
    LifecycleInvariantError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    SQLiteLifecycleStore,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"
NOW = datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc)


class SimulatedSolidWorksAdapter(TestDoubleCadAdapter):
    """Synthetic vendor identity only; deliberately not real-host evidence."""

    adapter_name = "SOLIDWORKS_2026"


def _sketch() -> dict:
    return json.loads((FIXTURE_ROOT / "sketch_package_v1.json").read_text(encoding="utf-8"))


def _runtime(*, mismatch: bool = False):
    overrides = {"D-WIDTH": 81.0} if mismatch else None
    return execute_cad_runtime_validation_v1(
        sketch_package=_sketch(),
        adapter=SimulatedSolidWorksAdapter(actual_overrides=overrides),
        cad_package_id="CAD-R4-X45",
        report_id="CADV-R4-X45",
        real_host_executed=False,
    )


def _prepare_revision(store: SQLiteLifecycleStore, runtime, *, revision_id: str):
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        revision = uow.cad_revisions.prepare(
            revision_id=revision_id,
            part_id="PART-GOLDEN-001",
            revision_code="REV04" if revision_id.endswith("UNVERIFIED") else "REV04-MISMATCH",
            created_at=NOW,
            cad_package=runtime.transfer_execution.cad_package,
            verification_report=runtime.transfer_execution.cad_verification_report,
            runtime_evidence=runtime.runtime_evidence,
            event_id=f"EV-{revision_id}",
        )
    return uow, revision


def test_round4_numerically_verified_but_runtime_unverified_is_fail_closed_in_lifecycle_and_read_model(
    tmp_path: Path,
) -> None:
    runtime = _runtime()
    assert runtime.verification_status == "VERIFIED"
    assert runtime.runtime_status == "UNVERIFIED"

    database = tmp_path / "round4-unverified.db"
    store = SQLiteLifecycleStore(database)
    uow, revision = _prepare_revision(store, runtime, revision_id="REV-R4-UNVERIFIED")

    assert revision.cad_link is not None
    assert hasattr(revision.cad_link, "runtime_status"), (
        "Chat 5 must persist Chat 4 runtime evidence/status for runtime-gated CAD origins"
    )
    assert str(revision.cad_link.runtime_status.value) == "UNVERIFIED"
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is False

    with pytest.raises(LifecycleInvariantError, match="not VERIFIED|runtime|UNVERIFIED"):
        with uow.transaction():
            uow.manufacturing.record(
                ManufacturingRecord(
                    manufacturing_id="MFG-R4-X45-BLOCKED",
                    revision_id=revision.revision_id,
                    material="PETG",
                    method="FDM",
                    manufactured_at=NOW,
                ),
                event_id="EV-R4-X45-MFG-BLOCKED",
            )

    rows = store.queries.revision_history("PART-GOLDEN-001")
    assert [row.revision_id for row in rows] == [revision.revision_id]
    assert "MFG-R4-X45-BLOCKED" not in store.manufacturing_records
    store.close()

    reopened = SQLiteLifecycleStore(database)
    reopened_revision = reopened.revisions[revision.revision_id]
    assert reopened_revision.cad_link is not None
    assert str(reopened_revision.cad_link.runtime_status.value) == "UNVERIFIED"
    assert LifecycleUnitOfWork(reopened).manufacturing.is_revision_eligible(revision.revision_id) is False
    reopened.close()


def test_round4_numerical_mismatch_is_also_fail_closed_when_runtime_is_unverified(tmp_path: Path) -> None:
    runtime = _runtime(mismatch=True)
    assert runtime.verification_status == "FAILED"
    assert runtime.runtime_status == "UNVERIFIED"

    store = SQLiteLifecycleStore(tmp_path / "round4-mismatch.db")
    uow, revision = _prepare_revision(store, runtime, revision_id="REV-R4-MISMATCH")
    assert revision.cad_link is not None
    assert str(revision.cad_link.runtime_status.value) == "UNVERIFIED"
    assert uow.manufacturing.is_revision_eligible(revision.revision_id) is False
    store.close()
