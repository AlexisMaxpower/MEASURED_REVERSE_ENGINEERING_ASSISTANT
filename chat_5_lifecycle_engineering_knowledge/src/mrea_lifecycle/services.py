from __future__ import annotations

from .models import (
    FailureRecord,
    Installation,
    LifecycleEventType,
    ManufacturingRecord,
    Revision,
    TestRecord,
)
from .store import InMemoryLifecycleStore, LifecycleInvariantError


class RevisionService:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def create(self, revision: Revision, *, event_id: str) -> Revision:
        if revision.revision_id in self.store.revisions:
            raise LifecycleInvariantError(f"duplicate revision_id: {revision.revision_id}")

        if any(
            existing.part_id == revision.part_id
            and existing.revision_code == revision.revision_code
            for existing in self.store.revisions.values()
        ):
            raise LifecycleInvariantError(
                f"revision_code already exists for part {revision.part_id}: {revision.revision_code}"
            )

        if revision.parent_revision_id is not None:
            parent = self.store.revisions.get(revision.parent_revision_id)
            if parent is None:
                raise LifecycleInvariantError(
                    f"unknown parent_revision_id: {revision.parent_revision_id}"
                )
            if parent.part_id != revision.part_id:
                raise LifecycleInvariantError("parent revision belongs to another part")

        self.store.revisions[revision.revision_id] = revision
        self.store.append_event(
            event_id=event_id,
            event_type=LifecycleEventType.REVISION_CREATED,
            occurred_at=revision.created_at,
            revision_id=revision.revision_id,
        )
        return revision


class ManufacturingService:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def record(self, record: ManufacturingRecord, *, event_id: str) -> ManufacturingRecord:
        if record.manufacturing_id in self.store.manufacturing_records:
            raise LifecycleInvariantError(
                f"duplicate manufacturing_id: {record.manufacturing_id}"
            )
        if record.revision_id not in self.store.revisions:
            raise LifecycleInvariantError(f"unknown revision_id: {record.revision_id}")

        self.store.manufacturing_records[record.manufacturing_id] = record
        self.store.append_event(
            event_id=event_id,
            event_type=LifecycleEventType.MANUFACTURED,
            occurred_at=record.manufactured_at,
            revision_id=record.revision_id,
            manufacturing_id=record.manufacturing_id,
        )
        return record


class InstallationService:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def install(self, installation: Installation, *, event_id: str) -> Installation:
        if installation.installation_id in self.store.installations:
            raise LifecycleInvariantError(
                f"duplicate installation_id: {installation.installation_id}"
            )

        revision = self.store.revisions.get(installation.revision_id)
        if revision is None:
            raise LifecycleInvariantError(f"unknown revision_id: {installation.revision_id}")

        manufacturing = self.store.manufacturing_records.get(
            installation.manufacturing_id
        )
        if manufacturing is None:
            raise LifecycleInvariantError(
                f"unknown manufacturing_id: {installation.manufacturing_id}"
            )
        if manufacturing.revision_id != revision.revision_id:
            raise LifecycleInvariantError(
                "installation revision does not match manufacturing revision"
            )

        self.store.installations[installation.installation_id] = installation
        self.store.append_event(
            event_id=event_id,
            event_type=LifecycleEventType.INSTALLED,
            occurred_at=installation.installed_at,
            revision_id=installation.revision_id,
            manufacturing_id=installation.manufacturing_id,
            installation_id=installation.installation_id,
        )
        return installation


class TestService:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def record(self, record: TestRecord, *, event_id: str) -> TestRecord:
        if record.test_id in self.store.tests:
            raise LifecycleInvariantError(f"duplicate test_id: {record.test_id}")
        if record.revision_id not in self.store.revisions:
            raise LifecycleInvariantError(f"unknown revision_id: {record.revision_id}")

        if record.manufacturing_id is not None:
            manufacturing = self.store.manufacturing_records.get(record.manufacturing_id)
            if manufacturing is None:
                raise LifecycleInvariantError(
                    f"unknown manufacturing_id: {record.manufacturing_id}"
                )
            if manufacturing.revision_id != record.revision_id:
                raise LifecycleInvariantError(
                    "test revision does not match manufacturing revision"
                )

        if record.installation_id is not None:
            installation = self.store.installations.get(record.installation_id)
            if installation is None:
                raise LifecycleInvariantError(
                    f"unknown installation_id: {record.installation_id}"
                )
            if installation.revision_id != record.revision_id:
                raise LifecycleInvariantError(
                    "test revision does not match installation revision"
                )

        self.store.tests[record.test_id] = record
        self.store.append_event(
            event_id=event_id,
            event_type=LifecycleEventType.TESTED,
            occurred_at=record.tested_at,
            revision_id=record.revision_id,
            manufacturing_id=record.manufacturing_id,
            installation_id=record.installation_id,
            test_id=record.test_id,
        )
        return record


class FailureService:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def record(self, record: FailureRecord, *, event_id: str) -> FailureRecord:
        if record.failure_id in self.store.failures:
            raise LifecycleInvariantError(f"duplicate failure_id: {record.failure_id}")
        if record.revision_id not in self.store.revisions:
            raise LifecycleInvariantError(f"unknown revision_id: {record.revision_id}")
        if not record.evidence_artifact_ids:
            raise LifecycleInvariantError("failure requires at least one evidence artifact")

        if record.manufacturing_id is not None:
            manufacturing = self.store.manufacturing_records.get(record.manufacturing_id)
            if manufacturing is None:
                raise LifecycleInvariantError(
                    f"unknown manufacturing_id: {record.manufacturing_id}"
                )
            if manufacturing.revision_id != record.revision_id:
                raise LifecycleInvariantError(
                    "failure revision does not match manufacturing revision"
                )

        if record.installation_id is not None:
            installation = self.store.installations.get(record.installation_id)
            if installation is None:
                raise LifecycleInvariantError(
                    f"unknown installation_id: {record.installation_id}"
                )
            if installation.revision_id != record.revision_id:
                raise LifecycleInvariantError(
                    "failure revision does not match installation revision"
                )

        self.store.failures[record.failure_id] = record
        self.store.append_event(
            event_id=event_id,
            event_type=LifecycleEventType.FAILED,
            occurred_at=record.failed_at,
            revision_id=record.revision_id,
            manufacturing_id=record.manufacturing_id,
            installation_id=record.installation_id,
            failure_id=record.failure_id,
        )
        return record
