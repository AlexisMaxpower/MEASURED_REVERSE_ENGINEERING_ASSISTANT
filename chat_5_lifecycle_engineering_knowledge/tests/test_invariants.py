from datetime import datetime, timezone

import pytest

from mrea_lifecycle import (
    FailureRecord,
    FailureService,
    InMemoryLifecycleStore,
    Installation,
    InstallationService,
    LifecycleInvariantError,
    ManufacturingRecord,
    ManufacturingService,
    Revision,
    RevisionService,
)


NOW = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)


def test_revision_code_cannot_be_reused_for_same_part() -> None:
    store = InMemoryLifecycleStore()
    service = RevisionService(store)

    service.create(
        Revision("R1", "P1", "REV01", NOW),
        event_id="E1",
    )

    with pytest.raises(LifecycleInvariantError, match="revision_code already exists"):
        service.create(
            Revision("R2", "P1", "REV01", NOW),
            event_id="E2",
        )


def test_installation_must_match_manufactured_revision() -> None:
    store = InMemoryLifecycleStore()
    revision_service = RevisionService(store)
    manufacturing_service = ManufacturingService(store)
    installation_service = InstallationService(store)

    revision_service.create(Revision("R1", "P1", "REV01", NOW), event_id="E1")
    revision_service.create(Revision("R2", "P1", "REV02", NOW), event_id="E2")
    manufacturing_service.record(
        ManufacturingRecord("M1", "R1", "PETG", "FDM", NOW),
        event_id="E3",
    )

    with pytest.raises(LifecycleInvariantError, match="does not match manufacturing"):
        installation_service.install(
            Installation("I1", "R2", "M1", "EQ1", "POS1", NOW),
            event_id="E4",
        )


def test_failure_requires_evidence_and_does_not_require_confirmed_cause() -> None:
    store = InMemoryLifecycleStore()
    revision_service = RevisionService(store)
    failure_service = FailureService(store)

    revision_service.create(Revision("R1", "P1", "REV01", NOW), event_id="E1")

    with pytest.raises(LifecycleInvariantError, match="evidence"):
        failure_service.record(
            FailureRecord(
                failure_id="F1",
                revision_id="R1",
                failed_at=NOW,
                failure_type="CRACK",
                damage_location="H2",
                circumstances="service",
                evidence_artifact_ids=(),
                estimated_cause="stress concentration",
                confirmed_cause=None,
            ),
            event_id="E2",
        )

    record = failure_service.record(
        FailureRecord(
            failure_id="F2",
            revision_id="R1",
            failed_at=NOW,
            failure_type="CRACK",
            damage_location="H2",
            circumstances="service",
            evidence_artifact_ids=("ART1",),
            estimated_cause="stress concentration",
            confirmed_cause=None,
        ),
        event_id="E3",
    )
    assert record.confirmed_cause is None
    assert record.estimated_cause == "stress concentration"
