from __future__ import annotations

import json
import sqlite3
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Mapping, Optional

from .models import (
    CADArtifactReference,
    CADRevisionLink,
    CADVerificationStatus,
    FailureRecord,
    Installation,
    LifecycleEvent,
    LifecycleEventType,
    ManufacturingRecord,
    PhysicalLifecycleEvent,
    PhysicalLifecycleEventType,
    PhysicalPartInstance,
    PhysicalTestOutcome,
    Revision,
    RevisionOrigin,
    TestRecord,
)
from .store import InMemoryLifecycleStore


SQLITE_SNAPSHOT_SCHEMA_VERSION = "mrea.lifecycle-snapshot.v1"


class LifecyclePersistenceError(RuntimeError):
    pass


class LifecycleConcurrencyError(LifecyclePersistenceError):
    pass


class LifecycleTransactionRequiredError(LifecyclePersistenceError):
    pass


def _encode_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return {"$type": "datetime", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"$type": "decimal", "value": str(value)}
    if is_dataclass(value):
        return {
            item.name: _encode_value(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _encode_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_encode_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise LifecyclePersistenceError(
        f"unsupported lifecycle persistence value: {type(value).__name__}"
    )


def _decode_value(value: object) -> object:
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    if isinstance(value, dict):
        marker = value.get("$type")
        if marker == "datetime" and set(value) == {"$type", "value"}:
            raw = value["value"]
            if not isinstance(raw, str):
                raise LifecyclePersistenceError("invalid persisted datetime")
            return datetime.fromisoformat(raw)
        if marker == "decimal" and set(value) == {"$type", "value"}:
            raw = value["value"]
            if not isinstance(raw, str):
                raise LifecyclePersistenceError("invalid persisted decimal")
            return Decimal(raw)
        return {key: _decode_value(item) for key, item in value.items()}
    return value


def _cad_link(raw: object) -> Optional[CADRevisionLink]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise LifecyclePersistenceError("invalid persisted CAD revision link")
    raw_artifacts = raw.get("artifacts", [])
    if not isinstance(raw_artifacts, list):
        raise LifecyclePersistenceError("invalid persisted CAD artifacts")
    artifacts = tuple(CADArtifactReference(**artifact) for artifact in raw_artifacts)
    return CADRevisionLink(
        cad_package_id=raw["cad_package_id"],
        sketch_package_id=raw["sketch_package_id"],
        cad_verification_report_id=raw["cad_verification_report_id"],
        cad_adapter=raw["cad_adapter"],
        verification_status=CADVerificationStatus(raw["verification_status"]),
        artifacts=artifacts,
    )


def _revision(raw: dict[str, object]) -> Revision:
    return Revision(
        revision_id=raw["revision_id"],
        part_id=raw["part_id"],
        revision_code=raw["revision_code"],
        created_at=raw["created_at"],
        parent_revision_id=raw.get("parent_revision_id"),
        notes=raw.get("notes"),
        source_cad_artifact_id=raw.get("source_cad_artifact_id"),
        origin=RevisionOrigin(raw["origin"]),
        cad_link=_cad_link(raw.get("cad_link")),
    )


def _test_record(raw: dict[str, object]) -> TestRecord:
    return TestRecord(
        test_id=raw["test_id"],
        revision_id=raw["revision_id"],
        tested_at=raw["tested_at"],
        test_type=raw["test_type"],
        conditions=raw["conditions"],
        result=raw["result"],
        conclusion=raw["conclusion"],
        manufacturing_id=raw.get("manufacturing_id"),
        installation_id=raw.get("installation_id"),
        artifact_ids=tuple(raw.get("artifact_ids", [])),
        instance_id=raw.get("instance_id"),
    )


def _failure_record(raw: dict[str, object]) -> FailureRecord:
    return FailureRecord(
        failure_id=raw["failure_id"],
        revision_id=raw["revision_id"],
        failed_at=raw["failed_at"],
        failure_type=raw["failure_type"],
        damage_location=raw["damage_location"],
        circumstances=raw["circumstances"],
        evidence_artifact_ids=tuple(raw.get("evidence_artifact_ids", [])),
        manufacturing_id=raw.get("manufacturing_id"),
        installation_id=raw.get("installation_id"),
        estimated_cause=raw.get("estimated_cause"),
        confirmed_cause=raw.get("confirmed_cause"),
        related_feature=raw.get("related_feature"),
        instance_id=raw.get("instance_id"),
    )


def _lifecycle_event(raw: dict[str, object]) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=raw["event_id"],
        event_type=LifecycleEventType(raw["event_type"]),
        occurred_at=raw["occurred_at"],
        sequence=raw["sequence"],
        revision_id=raw["revision_id"],
        manufacturing_id=raw.get("manufacturing_id"),
        installation_id=raw.get("installation_id"),
        test_id=raw.get("test_id"),
        failure_id=raw.get("failure_id"),
    )


def _physical_event(raw: dict[str, object]) -> PhysicalLifecycleEvent:
    test_outcome = raw.get("test_outcome")
    return PhysicalLifecycleEvent(
        event_id=raw["event_id"],
        event_type=PhysicalLifecycleEventType(raw["event_type"]),
        occurred_at=raw["occurred_at"],
        sequence=raw["sequence"],
        instance_id=raw["instance_id"],
        revision_id=raw["revision_id"],
        manufacturing_id=raw["manufacturing_id"],
        installation_id=raw.get("installation_id"),
        test_id=raw.get("test_id"),
        failure_id=raw.get("failure_id"),
        equipment_id=raw.get("equipment_id"),
        position=raw.get("position"),
        test_outcome=(
            PhysicalTestOutcome(test_outcome) if test_outcome is not None else None
        ),
        replacement_instance_id=raw.get("replacement_instance_id"),
        notes=raw.get("notes"),
    )


class SQLiteLifecycleStore(InMemoryLifecycleStore):
    """Durable Chat 5 repository with atomic snapshot commits and stale-writer guard.

    This is deliberately a persistence foundation rather than a query-optimized final
    schema. The complete lifecycle aggregate is serialized into one versioned SQLite
    snapshot so canonical and physical event streams commit atomically.
    """

    def __init__(self, database: str | Path, *, timeout: float = 5.0) -> None:
        super().__init__()
        self.database = str(database)
        self._connection = sqlite3.connect(
            self.database,
            timeout=timeout,
            isolation_level=None,
        )
        self._loaded_version = 0
        self._ensure_schema()
        self.reload()

    @property
    def loaded_version(self) -> int:
        return self._loaded_version

    def _ensure_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_store (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                schema_version TEXT NOT NULL,
                version INTEGER NOT NULL CHECK (version >= 0),
                payload TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            INSERT OR IGNORE INTO lifecycle_store(
                singleton, schema_version, version, payload
            ) VALUES (1, ?, 0, '{}')
            """,
            (SQLITE_SNAPSHOT_SCHEMA_VERSION,),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "revisions": _encode_value(self.revisions),
            "manufacturing_records": _encode_value(self.manufacturing_records),
            "installations": _encode_value(self.installations),
            "tests": _encode_value(self.tests),
            "failures": _encode_value(self.failures),
            "events": _encode_value(self.events),
            "physical_instances": _encode_value(self.physical_instances),
            "physical_events": _encode_value(self.physical_events),
        }

    def _hydrate(self, payload_text: str) -> None:
        try:
            parsed = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise LifecyclePersistenceError("invalid lifecycle snapshot JSON") from exc
        if not isinstance(parsed, dict):
            raise LifecyclePersistenceError("lifecycle snapshot must be an object")
        decoded = _decode_value(parsed)
        if not isinstance(decoded, dict):
            raise LifecyclePersistenceError("decoded lifecycle snapshot must be an object")

        revisions = decoded.get("revisions", {})
        manufacturing = decoded.get("manufacturing_records", {})
        installations = decoded.get("installations", {})
        tests = decoded.get("tests", {})
        failures = decoded.get("failures", {})
        events = decoded.get("events", [])
        physical_instances = decoded.get("physical_instances", {})
        physical_events = decoded.get("physical_events", [])

        if not all(
            isinstance(item, dict)
            for item in (
                revisions,
                manufacturing,
                installations,
                tests,
                failures,
                physical_instances,
            )
        ) or not isinstance(events, list) or not isinstance(physical_events, list):
            raise LifecyclePersistenceError("invalid lifecycle snapshot structure")

        self.revisions = {
            key: _revision(value) for key, value in revisions.items()
        }
        self.manufacturing_records = {
            key: ManufacturingRecord(**value) for key, value in manufacturing.items()
        }
        self.installations = {
            key: Installation(**value) for key, value in installations.items()
        }
        self.tests = {key: _test_record(value) for key, value in tests.items()}
        self.failures = {
            key: _failure_record(value) for key, value in failures.items()
        }
        self.events = [_lifecycle_event(value) for value in events]
        self.physical_instances = {
            key: PhysicalPartInstance(**value)
            for key, value in physical_instances.items()
        }
        self.physical_events = [_physical_event(value) for value in physical_events]
        self._sequence = max((event.sequence for event in self.events), default=0)
        self._physical_sequence = max(
            (event.sequence for event in self.physical_events), default=0
        )

    def reload(self) -> None:
        if self.transaction_depth:
            raise LifecyclePersistenceError("cannot reload during active transaction")
        row = self._connection.execute(
            """
            SELECT schema_version, version, payload
            FROM lifecycle_store
            WHERE singleton = 1
            """
        ).fetchone()
        if row is None:
            raise LifecyclePersistenceError("lifecycle snapshot row is missing")
        schema_version, version, payload = row
        if schema_version != SQLITE_SNAPSHOT_SCHEMA_VERSION:
            raise LifecyclePersistenceError(
                f"unsupported lifecycle snapshot schema: {schema_version}"
            )
        self._hydrate(payload)
        self._loaded_version = int(version)

    def _begin_outer_transaction(self) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        row = self._connection.execute(
            "SELECT version FROM lifecycle_store WHERE singleton = 1"
        ).fetchone()
        if row is None:
            self._connection.rollback()
            raise LifecyclePersistenceError("lifecycle snapshot row is missing")
        current_version = int(row[0])
        if current_version != self._loaded_version:
            self._connection.rollback()
            raise LifecycleConcurrencyError(
                "stale lifecycle repository; reload before writing "
                f"(loaded={self._loaded_version}, current={current_version})"
            )

    def _commit_outer_transaction(self) -> None:
        payload = json.dumps(
            self._payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        next_version = self._loaded_version + 1
        cursor = self._connection.execute(
            """
            UPDATE lifecycle_store
            SET schema_version = ?, version = ?, payload = ?
            WHERE singleton = 1 AND version = ?
            """,
            (
                SQLITE_SNAPSHOT_SCHEMA_VERSION,
                next_version,
                payload,
                self._loaded_version,
            ),
        )
        if cursor.rowcount != 1:
            raise LifecycleConcurrencyError(
                "lifecycle snapshot changed during commit"
            )
        self._connection.commit()
        self._loaded_version = next_version

    def _rollback_outer_transaction(self) -> None:
        if self._connection.in_transaction:
            self._connection.rollback()

    def _require_active_transaction(self) -> None:
        if self.transaction_depth:
            return
        # A legacy service may mutate an in-memory mapping before it appends the event.
        # Reloading here discards that unsafely staged mutation before failing closed.
        self.reload()
        raise LifecycleTransactionRequiredError(
            "SQLite lifecycle mutations require LifecycleUnitOfWork.transaction()"
        )

    def append_event(
        self,
        *,
        event_id: str,
        event_type: LifecycleEventType,
        occurred_at: datetime,
        revision_id: str,
        manufacturing_id: Optional[str] = None,
        installation_id: Optional[str] = None,
        test_id: Optional[str] = None,
        failure_id: Optional[str] = None,
    ) -> LifecycleEvent:
        self._require_active_transaction()
        return super().append_event(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            revision_id=revision_id,
            manufacturing_id=manufacturing_id,
            installation_id=installation_id,
            test_id=test_id,
            failure_id=failure_id,
        )

    def append_physical_event(
        self,
        *,
        event_id: str,
        event_type: PhysicalLifecycleEventType,
        occurred_at: datetime,
        instance_id: str,
        revision_id: str,
        manufacturing_id: str,
        installation_id: Optional[str] = None,
        test_id: Optional[str] = None,
        failure_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        position: Optional[str] = None,
        test_outcome: Optional[PhysicalTestOutcome] = None,
        replacement_instance_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PhysicalLifecycleEvent:
        self._require_active_transaction()
        return super().append_physical_event(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            instance_id=instance_id,
            revision_id=revision_id,
            manufacturing_id=manufacturing_id,
            installation_id=installation_id,
            test_id=test_id,
            failure_id=failure_id,
            equipment_id=equipment_id,
            position=position,
            test_outcome=test_outcome,
            replacement_instance_id=replacement_instance_id,
            notes=notes,
        )

    def close(self) -> None:
        if self._connection.in_transaction:
            self._connection.rollback()
        self._connection.close()

    def __enter__(self) -> SQLiteLifecycleStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
