from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mrea_cad_bridge import TestDoubleCadAdapter, execute_cad_transfer_v1
from mrea_lifecycle import (
    CADRevisionPreparationService,
    InMemoryLifecycleStore,
    LifecycleInvariantError,
    ManufacturingRecord,
    ManufacturingService,
    RevisionOrigin,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"
NOW = datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc)


def _load(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _produce_cad(*, overrides: dict[str, float] | None = None):
    return execute_cad_transfer_v1(
        sketch_package=_load("sketch_package_v1.json"),
        adapter=TestDoubleCadAdapter(actual_overrides=overrides),
        cad_package_id="CAD-XSLICE-001",
        report_id="CADV-XSLICE-001",
    )


def test_real_chat4_verified_output_becomes_manufacturing_eligible_in_chat5() -> None:
    transfer = _produce_cad()

    assert transfer.cad_verification_report["overall_status"] == "VERIFIED"

    store = InMemoryLifecycleStore()
    revision = CADRevisionPreparationService(store).prepare(
        revision_id="REV-XSLICE-001",
        part_id="PART-GOLDEN-001",
        revision_code="REV01",
        created_at=NOW,
        cad_package=transfer.cad_package,
        verification_report=transfer.cad_verification_report,
        event_id="EV-XSLICE-REV-001",
    )

    assert revision.origin is RevisionOrigin.CAD_TRANSFER
    assert revision.cad_link is not None
    assert revision.cad_link.cad_package_id == transfer.cad_package["cad_package_id"]
    assert revision.cad_link.sketch_package_id == transfer.cad_package["sketch_package_id"]
    assert revision.cad_link.cad_verification_report_id == transfer.cad_verification_report["report_id"]
    assert revision.cad_link.cad_adapter == "TEST_DOUBLE"

    manufacturing = ManufacturingService(store)
    assert manufacturing.is_revision_eligible(revision.revision_id) is True
    manufacturing.record(
        ManufacturingRecord(
            manufacturing_id="MFG-XSLICE-001",
            revision_id=revision.revision_id,
            material="PETG",
            method="FDM",
            manufactured_at=NOW,
        ),
        event_id="EV-XSLICE-MFG-001",
    )

    assert "MFG-XSLICE-001" in store.manufacturing_records


def test_real_chat4_failed_verification_is_retained_but_blocks_manufacturing() -> None:
    transfer = _produce_cad(overrides={"D-WIDTH": 81.0})

    assert transfer.cad_verification_report["overall_status"] == "FAILED"

    store = InMemoryLifecycleStore()
    revision = CADRevisionPreparationService(store).prepare(
        revision_id="REV-XSLICE-FAILED",
        part_id="PART-GOLDEN-001",
        revision_code="REV01",
        created_at=NOW,
        cad_package=transfer.cad_package,
        verification_report=transfer.cad_verification_report,
        event_id="EV-XSLICE-REV-FAILED",
    )

    manufacturing = ManufacturingService(store)
    assert manufacturing.is_revision_eligible(revision.revision_id) is False

    with pytest.raises(LifecycleInvariantError, match="not VERIFIED"):
        manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="MFG-XSLICE-BLOCKED",
                revision_id=revision.revision_id,
                material="PETG",
                method="FDM",
                manufactured_at=NOW,
            ),
            event_id="EV-XSLICE-MFG-BLOCKED",
        )

    assert "MFG-XSLICE-BLOCKED" not in store.manufacturing_records
