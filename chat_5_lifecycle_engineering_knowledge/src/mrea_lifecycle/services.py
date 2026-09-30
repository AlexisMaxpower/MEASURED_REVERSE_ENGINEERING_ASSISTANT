from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Mapping, Optional

from .models import (
    CADArtifactReference,
    CADRevisionLink,
    CADRuntimeStatus,
    CADVerificationStatus,
    FailureRecord,
    Installation,
    LifecycleEventType,
    ManufacturingRecord,
    Revision,
    RevisionOrigin,
    TestRecord,
)
from .store import InMemoryLifecycleStore, LifecycleInvariantError


CAD_PACKAGE_SCHEMA_VERSION = "mrea.cad-package.v1"
CAD_VERIFICATION_SCHEMA_VERSION = "mrea.cad-verification.v1"
CAD_RUNTIME_EVIDENCE_SCHEMA_VERSION = "mrea.cad-runtime-evidence.v1"
_ALLOWED_ARTIFACT_FIELDS = {
    "artifact_id",
    "kind",
    "uri",
    "media_type",
    "sha256",
    "metadata",
}


def _require_non_empty_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifecycleInvariantError(f"{field_name} must be a non-empty string")
    return value


def _require_mapping(value: object, *, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LifecycleInvariantError(f"{field_name} must be an object")
    return value


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

        if revision.origin is RevisionOrigin.CAD_TRANSFER and revision.cad_link is None:
            raise LifecycleInvariantError(
                "CAD_TRANSFER revision requires explicit CAD revision linkage"
            )
        if revision.origin is RevisionOrigin.MANUAL and revision.cad_link is not None:
            raise LifecycleInvariantError(
                "manual revision cannot silently carry CAD transfer linkage"
            )

        self.store.revisions[revision.revision_id] = revision
        self.store.append_event(
            event_id=event_id,
            event_type=LifecycleEventType.REVISION_CREATED,
            occurred_at=revision.created_at,
            revision_id=revision.revision_id,
        )
        return revision


class CADRevisionPreparationService:
    """Consumes canonical CAD outputs and creates a traceable lifecycle Revision."""

    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store
        self.revisions = RevisionService(store)

    def prepare(
        self,
        *,
        revision_id: str,
        part_id: str,
        revision_code: str,
        created_at: datetime,
        cad_package: Mapping[str, object],
        verification_report: Mapping[str, object],
        event_id: str,
        parent_revision_id: Optional[str] = None,
        notes: Optional[str] = None,
        runtime_evidence: Optional[Mapping[str, object]] = None,
    ) -> Revision:
        package = _require_mapping(cad_package, field_name="cad_package")
        report = _require_mapping(
            verification_report, field_name="verification_report"
        )

        if package.get("schema_version") != CAD_PACKAGE_SCHEMA_VERSION:
            raise LifecycleInvariantError("unsupported CADPackage schema_version")
        if report.get("schema_version") != CAD_VERIFICATION_SCHEMA_VERSION:
            raise LifecycleInvariantError(
                "unsupported CADVerificationReport schema_version"
            )

        cad_package_id = _require_non_empty_string(
            package.get("cad_package_id"), field_name="cad_package_id"
        )
        sketch_package_id = _require_non_empty_string(
            package.get("sketch_package_id"), field_name="sketch_package_id"
        )
        cad_adapter = _require_non_empty_string(
            package.get("adapter"), field_name="adapter"
        )
        report_id = _require_non_empty_string(
            report.get("report_id"), field_name="report_id"
        )
        report_cad_package_id = _require_non_empty_string(
            report.get("cad_package_id"), field_name="report.cad_package_id"
        )
        report_sketch_package_id = _require_non_empty_string(
            report.get("sketch_package_id"), field_name="report.sketch_package_id"
        )

        if report_cad_package_id != cad_package_id:
            raise LifecycleInvariantError(
                "CADVerificationReport cad_package_id does not match CADPackage"
            )
        if report_sketch_package_id != sketch_package_id:
            raise LifecycleInvariantError(
                "CADVerificationReport sketch_package_id does not match CADPackage"
            )

        raw_status = report.get("overall_status")
        try:
            verification_status = CADVerificationStatus(raw_status)
        except (TypeError, ValueError) as exc:
            raise LifecycleInvariantError(
                "CADVerificationReport overall_status must be VERIFIED or FAILED"
            ) from exc

        runtime_status: Optional[CADRuntimeStatus] = None
        runtime_schema_version: Optional[str] = None
        runtime_real_host_executed: Optional[bool] = None
        if runtime_evidence is not None:
            evidence = _require_mapping(
                runtime_evidence, field_name="runtime_evidence"
            )
            runtime_schema_version = _require_non_empty_string(
                evidence.get("schema_version"),
                field_name="runtime_evidence.schema_version",
            )
            if runtime_schema_version != CAD_RUNTIME_EVIDENCE_SCHEMA_VERSION:
                raise LifecycleInvariantError(
                    "unsupported CAD runtime evidence schema_version"
                )
            try:
                runtime_status = CADRuntimeStatus(evidence.get("status"))
            except (TypeError, ValueError) as exc:
                raise LifecycleInvariantError(
                    "runtime evidence status must be VERIFIED, FAILED, or UNVERIFIED"
                ) from exc

            runtime_adapter = _require_non_empty_string(
                evidence.get("adapter_name"),
                field_name="runtime_evidence.adapter_name",
            )
            if runtime_adapter != cad_adapter:
                raise LifecycleInvariantError(
                    "runtime evidence adapter_name does not match CADPackage adapter"
                )

            runtime_sketch_package_id = _require_non_empty_string(
                evidence.get("sketch_package_id"),
                field_name="runtime_evidence.sketch_package_id",
            )
            if runtime_sketch_package_id != sketch_package_id:
                raise LifecycleInvariantError(
                    "runtime evidence sketch_package_id does not match CADPackage"
                )

            runtime_cad_package_id = evidence.get("cad_package_id")
            if runtime_cad_package_id is not None:
                runtime_cad_package_id = _require_non_empty_string(
                    runtime_cad_package_id,
                    field_name="runtime_evidence.cad_package_id",
                )
                if runtime_cad_package_id != cad_package_id:
                    raise LifecycleInvariantError(
                        "runtime evidence cad_package_id does not match CADPackage"
                    )

            raw_real_host_executed = evidence.get("real_host_executed")
            if not isinstance(raw_real_host_executed, bool):
                raise LifecycleInvariantError(
                    "runtime_evidence.real_host_executed must be boolean"
                )
            runtime_real_host_executed = raw_real_host_executed
            if runtime_status is CADRuntimeStatus.VERIFIED and not runtime_real_host_executed:
                raise LifecycleInvariantError(
                    "runtime VERIFIED requires real_host_executed=true"
                )

        raw_artifacts = package.get("artifacts")
        if not isinstance(raw_artifacts, list):
            raise LifecycleInvariantError("CADPackage artifacts must be an array")

        artifacts: list[CADArtifactReference] = []
        for index, raw_artifact in enumerate(raw_artifacts):
            artifact = _require_mapping(
                raw_artifact, field_name=f"artifacts[{index}]"
            )
            unexpected = set(artifact) - _ALLOWED_ARTIFACT_FIELDS
            if unexpected:
                raise LifecycleInvariantError(
                    f"artifacts[{index}] contains unsupported fields: {sorted(unexpected)}"
                )
            metadata = artifact.get("metadata", {})
            if not isinstance(metadata, Mapping):
                raise LifecycleInvariantError(
                    f"artifacts[{index}].metadata must be an object"
                )
            media_type = artifact.get("media_type")
            if media_type is not None and not isinstance(media_type, str):
                raise LifecycleInvariantError(
                    f"artifacts[{index}].media_type must be string or null"
                )
            sha256 = artifact.get("sha256")
            if sha256 is not None and not isinstance(sha256, str):
                raise LifecycleInvariantError(
                    f"artifacts[{index}].sha256 must be string or null"
                )

            artifacts.append(
                CADArtifactReference(
                    artifact_id=_require_non_empty_string(
                        artifact.get("artifact_id"),
                        field_name=f"artifacts[{index}].artifact_id",
                    ),
                    kind=_require_non_empty_string(
                        artifact.get("kind"), field_name=f"artifacts[{index}].kind"
                    ),
                    uri=_require_non_empty_string(
                        artifact.get("uri"), field_name=f"artifacts[{index}].uri"
                    ),
                    media_type=media_type,
                    sha256=sha256,
                    metadata=deepcopy(dict(metadata)),
                )
            )

        revision = Revision(
            revision_id=revision_id,
            part_id=part_id,
            revision_code=revision_code,
            created_at=created_at,
            parent_revision_id=parent_revision_id,
            notes=notes,
            origin=RevisionOrigin.CAD_TRANSFER,
            cad_link=CADRevisionLink(
                cad_package_id=cad_package_id,
                sketch_package_id=sketch_package_id,
                cad_verification_report_id=report_id,
                cad_adapter=cad_adapter,
                verification_status=verification_status,
                artifacts=tuple(artifacts),
                runtime_status=runtime_status,
                runtime_evidence_schema_version=runtime_schema_version,
                runtime_real_host_executed=runtime_real_host_executed,
            ),
        )
        return self.revisions.create(revision, event_id=event_id)


class ManufacturingService:
    def __init__(self, store: InMemoryLifecycleStore) -> None:
        self.store = store

    def is_revision_eligible(self, revision_id: str) -> bool:
        revision = self.store.revisions.get(revision_id)
        if revision is None:
            raise LifecycleInvariantError(f"unknown revision_id: {revision_id}")

        if revision.origin is not RevisionOrigin.CAD_TRANSFER:
            return True

        if revision.cad_link is None:
            return False
        if revision.cad_link.verification_status is not CADVerificationStatus.VERIFIED:
            return False
        if (
            revision.cad_link.runtime_status is not None
            and revision.cad_link.runtime_status is not CADRuntimeStatus.VERIFIED
        ):
            return False
        return True

    def record(self, record: ManufacturingRecord, *, event_id: str) -> ManufacturingRecord:
        if record.manufacturing_id in self.store.manufacturing_records:
            raise LifecycleInvariantError(
                f"duplicate manufacturing_id: {record.manufacturing_id}"
            )
        revision = self.store.revisions.get(record.revision_id)
        if revision is None:
            raise LifecycleInvariantError(f"unknown revision_id: {record.revision_id}")
        if not self.is_revision_eligible(record.revision_id):
            raise LifecycleInvariantError(
                "CAD transfer verification/runtime gate is not VERIFIED; manufacturing is blocked"
            )

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
