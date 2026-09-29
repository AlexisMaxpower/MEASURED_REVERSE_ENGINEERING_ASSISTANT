import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mrea_lifecycle import (
    CANONICAL_LIFECYCLE_EVENT_SCHEMA_VERSION,
    CANONICAL_LIFECYCLE_EVENT_TYPES,
    CanonicalLifecycleEventAdapter,
    FailureRecord,
    FailureService,
    InMemoryLifecycleStore,
    Installation,
    InstallationService,
    LifecycleEvent,
    LifecycleEventType,
    LifecycleInvariantError,
    ManufacturingRecord,
    ManufacturingService,
    Revision,
    RevisionService,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_adapter_constants_match_integrator_owned_schema() -> None:
    schema = json.loads(
        (REPO_ROOT / "core/contracts/mrea_contracts_v1.schema.json").read_text()
    )
    lifecycle_schema = schema["$defs"]["LifecycleEvent"]

    assert (
        lifecycle_schema["properties"]["schema_version"]["const"]
        == CANONICAL_LIFECYCLE_EVENT_SCHEMA_VERSION
    )
    assert set(lifecycle_schema["properties"]["event_type"]["enum"]) == set(
        CANONICAL_LIFECYCLE_EVENT_TYPES
    )


def test_revision_created_matches_canonical_golden_fixture() -> None:
    fixture = json.loads(
        (REPO_ROOT / "tests/fixtures/contracts/lifecycle_event_v1.json").read_text()
    )
    internal = LifecycleEvent(
        event_id=fixture["event_id"],
        event_type=LifecycleEventType.REVISION_CREATED,
        occurred_at=datetime(2026, 9, 29, 15, 10, tzinfo=timezone.utc),
        sequence=fixture["sequence"],
        revision_id=fixture["revision_id"],
    )

    assert CanonicalLifecycleEventAdapter.to_contract(internal) == fixture


def test_directive_acceptance_flow_exports_ordered_events_and_preserves_evidence() -> None:
    store = InMemoryLifecycleStore()
    revisions = RevisionService(store)
    manufacturing = ManufacturingService(store)
    installations = InstallationService(store)
    failures = FailureService(store)
    t0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)

    revisions.create(
        Revision("R1", "P1", "REV01", t0),
        event_id="E1",
    )
    manufacturing.record(
        ManufacturingRecord("M1", "R1", "PETG", "FDM", t0 + timedelta(hours=1)),
        event_id="E2",
    )
    installations.install(
        Installation("I1", "R1", "M1", "EQ1", "POS1", t0 + timedelta(hours=2)),
        event_id="E3",
    )
    failures.record(
        FailureRecord(
            failure_id="F1",
            revision_id="R1",
            failed_at=t0 + timedelta(days=1),
            failure_type="CRACK",
            damage_location="H2",
            circumstances="service",
            evidence_artifact_ids=("ART-FAIL-001",),
            manufacturing_id="M1",
            installation_id="I1",
        ),
        event_id="E4",
    )
    revisions.create(
        Revision("R2", "P1", "REV02", t0 + timedelta(days=2), parent_revision_id="R1"),
        event_id="E5",
    )

    exported = CanonicalLifecycleEventAdapter().export(reversed(store.events))

    assert [event["sequence"] for event in exported] == [1, 2, 3, 4, 5]
    assert [event["event_type"] for event in exported] == [
        "REVISION_CREATED",
        "MANUFACTURED",
        "INSTALLED",
        "FAILED",
        "REVISION_CREATED",
    ]
    assert exported[1]["manufacturing_id"] == "M1"
    assert exported[2]["installation_id"] == "I1"
    assert exported[3]["failure_id"] == "F1"
    assert store.failures["F1"].evidence_artifact_ids == ("ART-FAIL-001",)


def test_adapter_rejects_naive_timestamp() -> None:
    internal = LifecycleEvent(
        event_id="E1",
        event_type=LifecycleEventType.REVISION_CREATED,
        occurred_at=datetime(2026, 9, 29, 10, 0),
        sequence=1,
        revision_id="R1",
    )

    with pytest.raises(LifecycleInvariantError, match="timezone-aware"):
        CanonicalLifecycleEventAdapter.to_contract(internal)
