import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mrea_lifecycle import (
    CADRevisionPreparationService,
    CADVerificationStatus,
    CanonicalLifecycleEventAdapter,
    InMemoryLifecycleStore,
    LifecycleInvariantError,
    ManufacturingRecord,
    ManufacturingService,
    RevisionOrigin,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc)


def _fixtures() -> tuple[dict[str, object], dict[str, object]]:
    cad_package = json.loads(
        (REPO_ROOT / "tests/fixtures/contracts/cad_package_v1.json").read_text()
    )
    report = json.loads(
        (REPO_ROOT / "tests/fixtures/contracts/cad_verification_v1.json").read_text()
    )
    return cad_package, report


def test_verified_cad_report_allows_manufacturing_and_retains_traceability() -> None:
    store = InMemoryLifecycleStore()
    preparation = CADRevisionPreparationService(store)
    manufacturing = ManufacturingService(store)
    cad_package, report = _fixtures()
    cad_package["artifacts"] = [
        {
            "artifact_id": "ART-CAD-NATIVE-001",
            "kind": "SOLIDWORKS_NATIVE",
            "uri": "artifact://cad/native/part.SLDPRT",
            "media_type": "application/octet-stream",
            "sha256": "abc123",
            "metadata": {"role": "native", "revision": 1},
        },
        {
            "artifact_id": "ART-CAD-STEP-001",
            "kind": "STEP",
            "uri": "artifact://cad/export/part.step",
        },
    ]

    revision = preparation.prepare(
        revision_id="R-CAD-1",
        part_id="P-CAD-1",
        revision_code="REV01",
        created_at=NOW,
        cad_package=cad_package,
        verification_report=report,
        event_id="E-CAD-1",
    )

    assert revision.origin is RevisionOrigin.CAD_TRANSFER
    assert revision.cad_link is not None
    assert revision.cad_link.cad_package_id == "CAD-GOLDEN-001"
    assert revision.cad_link.sketch_package_id == "SP-GOLDEN-001"
    assert revision.cad_link.cad_verification_report_id == "VR-GOLDEN-001"
    assert revision.cad_link.verification_status is CADVerificationStatus.VERIFIED
    assert [artifact.artifact_id for artifact in revision.cad_link.artifacts] == [
        "ART-CAD-NATIVE-001",
        "ART-CAD-STEP-001",
    ]
    assert revision.cad_link.artifacts[0].metadata == {
        "role": "native",
        "revision": 1,
    }
    cad_package["artifacts"][0]["metadata"]["role"] = "mutated-after-prepare"
    assert revision.cad_link.artifacts[0].metadata["role"] == "native"
    assert manufacturing.is_revision_eligible(revision.revision_id) is True

    manufacturing.record(
        ManufacturingRecord(
            manufacturing_id="M-CAD-1",
            revision_id=revision.revision_id,
            material="PETG",
            method="FDM",
            manufactured_at=NOW + timedelta(hours=1),
        ),
        event_id="E-CAD-2",
    )

    exported = CanonicalLifecycleEventAdapter().export(store.events)
    assert [event["event_type"] for event in exported] == [
        "REVISION_CREATED",
        "MANUFACTURED",
    ]
    assert exported[0]["revision_id"] == "R-CAD-1"
    assert exported[1]["manufacturing_id"] == "M-CAD-1"


def test_failed_cad_report_creates_traceable_revision_but_blocks_manufacturing() -> None:
    store = InMemoryLifecycleStore()
    preparation = CADRevisionPreparationService(store)
    manufacturing = ManufacturingService(store)
    cad_package, report = _fixtures()
    report["overall_status"] = "FAILED"

    revision = preparation.prepare(
        revision_id="R-CAD-FAILED",
        part_id="P-CAD-1",
        revision_code="REV01",
        created_at=NOW,
        cad_package=cad_package,
        verification_report=report,
        event_id="E-CAD-FAILED-1",
    )

    assert revision.cad_link is not None
    assert revision.cad_link.verification_status is CADVerificationStatus.FAILED
    assert manufacturing.is_revision_eligible(revision.revision_id) is False

    with pytest.raises(LifecycleInvariantError, match="not VERIFIED"):
        manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M-BLOCKED",
                revision_id=revision.revision_id,
                material="PETG",
                method="FDM",
                manufactured_at=NOW + timedelta(hours=1),
            ),
            event_id="E-CAD-FAILED-2",
        )

    assert "M-BLOCKED" not in store.manufacturing_records
    assert [event.event_type.value for event in store.events] == ["REVISION_CREATED"]


@pytest.mark.parametrize(
    ("field_name", "replacement", "message"),
    [
        ("cad_package_id", "CAD-OTHER", "cad_package_id does not match"),
        ("sketch_package_id", "SP-OTHER", "sketch_package_id does not match"),
    ],
)
def test_mismatched_cad_package_and_verification_report_are_rejected(
    field_name: str, replacement: str, message: str
) -> None:
    store = InMemoryLifecycleStore()
    preparation = CADRevisionPreparationService(store)
    cad_package, report = _fixtures()
    report[field_name] = replacement

    with pytest.raises(LifecycleInvariantError, match=message):
        preparation.prepare(
            revision_id="R-MISMATCH",
            part_id="P-CAD-1",
            revision_code="REV01",
            created_at=NOW,
            cad_package=cad_package,
            verification_report=report,
            event_id="E-MISMATCH",
        )

    assert store.revisions == {}
    assert store.events == []


def test_missing_or_unverified_report_cannot_silently_enter_cad_path() -> None:
    store = InMemoryLifecycleStore()
    preparation = CADRevisionPreparationService(store)
    cad_package, report = _fixtures()
    invalid_report = copy.deepcopy(report)
    invalid_report["overall_status"] = "UNVERIFIED"

    with pytest.raises(LifecycleInvariantError, match="VERIFIED or FAILED"):
        preparation.prepare(
            revision_id="R-UNVERIFIED",
            part_id="P-CAD-1",
            revision_code="REV01",
            created_at=NOW,
            cad_package=cad_package,
            verification_report=invalid_report,
            event_id="E-UNVERIFIED",
        )

    with pytest.raises(LifecycleInvariantError, match="verification_report must be an object"):
        preparation.prepare(
            revision_id="R-MISSING",
            part_id="P-CAD-1",
            revision_code="REV02",
            created_at=NOW,
            cad_package=cad_package,
            verification_report=None,  # type: ignore[arg-type]
            event_id="E-MISSING",
        )
