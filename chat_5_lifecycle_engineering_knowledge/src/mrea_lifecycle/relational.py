from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from typing import Optional

from .repository import LifecycleRepository


@dataclass(frozen=True, slots=True)
class RevisionQueryResult:
    revision_id: str
    part_id: str
    revision_code: str
    created_at: datetime
    origin: str
    verification_status: Optional[str]
    runtime_status: Optional[str]
    runtime_evidence_schema_version: Optional[str]
    runtime_real_host_executed: Optional[bool]


@dataclass(frozen=True, slots=True)
class FailureQueryResult:
    failure_id: str
    revision_id: str
    instance_id: Optional[str]
    failed_at: datetime
    failure_type: str
    damage_location: str
    confirmed_cause: Optional[str]
    equipment_id: Optional[str]
    position: Optional[str]


@dataclass(frozen=True, slots=True)
class EquipmentOccupancyQueryResult:
    instance_id: str
    part_id: str
    revision_id: str
    manufacturing_id: str
    equipment_id: str
    position: str
    state: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PhysicalEventQueryResult:
    event_id: str
    event_type: str
    occurred_at: datetime
    sequence: int
    instance_id: str
    revision_id: str
    manufacturing_id: str
    installation_id: Optional[str]
    test_id: Optional[str]
    failure_id: Optional[str]
    equipment_id: Optional[str]
    position: Optional[str]
    test_outcome: Optional[str]
    replacement_instance_id: Optional[str]
    notes: Optional[str]


class SQLiteLifecycleReadModelWriter:
    """Rebuilds the normalized SQL read model from the authoritative aggregate."""

    _DELETE_ORDER = (
        "lifecycle_physical_events_relational",
        "lifecycle_events_relational",
        "lifecycle_failure_evidence",
        "lifecycle_failures",
        "lifecycle_test_artifacts",
        "lifecycle_tests",
        "lifecycle_installations",
        "lifecycle_physical_instances",
        "lifecycle_manufacturing",
        "lifecycle_cad_artifacts",
        "lifecycle_revisions",
    )

    @classmethod
    def replace(
        cls,
        connection: sqlite3.Connection,
        repository: LifecycleRepository,
    ) -> None:
        for table in cls._DELETE_ORDER:
            connection.execute(f"DELETE FROM {table}")

        for revision in sorted(
            repository.revisions.values(), key=lambda item: item.revision_id
        ):
            cad_link = revision.cad_link
            connection.execute(
                """
                INSERT INTO lifecycle_revisions(
                    revision_id, part_id, revision_code, created_at,
                    parent_revision_id, notes, source_cad_artifact_id, origin,
                    cad_package_id, sketch_package_id,
                    cad_verification_report_id, cad_adapter, verification_status,
                    runtime_status, runtime_evidence_schema_version,
                    runtime_real_host_executed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.part_id,
                    revision.revision_code,
                    revision.created_at.isoformat(),
                    revision.parent_revision_id,
                    revision.notes,
                    revision.source_cad_artifact_id,
                    revision.origin.value,
                    cad_link.cad_package_id if cad_link is not None else None,
                    cad_link.sketch_package_id if cad_link is not None else None,
                    (
                        cad_link.cad_verification_report_id
                        if cad_link is not None
                        else None
                    ),
                    cad_link.cad_adapter if cad_link is not None else None,
                    (
                        cad_link.verification_status.value
                        if cad_link is not None
                        else None
                    ),
                    (
                        cad_link.runtime_status.value
                        if cad_link is not None and cad_link.runtime_status is not None
                        else None
                    ),
                    (
                        cad_link.runtime_evidence_schema_version
                        if cad_link is not None
                        else None
                    ),
                    (
                        int(cad_link.runtime_real_host_executed)
                        if cad_link is not None
                        and cad_link.runtime_real_host_executed is not None
                        else None
                    ),
                ),
            )
            if cad_link is None:
                continue
            for ordinal, artifact in enumerate(cad_link.artifacts, start=1):
                connection.execute(
                    """
                    INSERT INTO lifecycle_cad_artifacts(
                        revision_id, ordinal, artifact_id, kind, uri,
                        media_type, sha256, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.revision_id,
                        ordinal,
                        artifact.artifact_id,
                        artifact.kind,
                        artifact.uri,
                        artifact.media_type,
                        artifact.sha256,
                        json.dumps(
                            dict(artifact.metadata),
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ),
                )

        for record in sorted(
            repository.manufacturing_records.values(),
            key=lambda item: item.manufacturing_id,
        ):
            connection.execute(
                """
                INSERT INTO lifecycle_manufacturing(
                    manufacturing_id, revision_id, material, method,
                    manufactured_at, batch, machine, print_profile,
                    contractor, cost, post_processing
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.manufacturing_id,
                    record.revision_id,
                    record.material,
                    record.method,
                    record.manufactured_at.isoformat(),
                    record.batch,
                    record.machine,
                    record.print_profile,
                    record.contractor,
                    str(record.cost) if record.cost is not None else None,
                    record.post_processing,
                ),
            )

        for instance in sorted(
            repository.physical_instances.values(),
            key=lambda item: item.instance_id,
        ):
            connection.execute(
                """
                INSERT INTO lifecycle_physical_instances(
                    instance_id, part_id, revision_id, manufacturing_id,
                    material, method, manufactured_at, batch, machine,
                    print_profile
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance.instance_id,
                    instance.part_id,
                    instance.revision_id,
                    instance.manufacturing_id,
                    instance.material,
                    instance.method,
                    instance.manufactured_at.isoformat(),
                    instance.batch,
                    instance.machine,
                    instance.print_profile,
                ),
            )

        for installation in sorted(
            repository.installations.values(),
            key=lambda item: item.installation_id,
        ):
            connection.execute(
                """
                INSERT INTO lifecycle_installations(
                    installation_id, revision_id, manufacturing_id,
                    equipment_id, position, installed_at, technician,
                    notes, instance_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    installation.installation_id,
                    installation.revision_id,
                    installation.manufacturing_id,
                    installation.equipment_id,
                    installation.position,
                    installation.installed_at.isoformat(),
                    installation.technician,
                    installation.notes,
                    installation.instance_id,
                ),
            )

        for record in sorted(repository.tests.values(), key=lambda item: item.test_id):
            connection.execute(
                """
                INSERT INTO lifecycle_tests(
                    test_id, revision_id, tested_at, test_type, conditions,
                    result, conclusion, manufacturing_id, installation_id,
                    instance_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.test_id,
                    record.revision_id,
                    record.tested_at.isoformat(),
                    record.test_type,
                    record.conditions,
                    record.result,
                    record.conclusion,
                    record.manufacturing_id,
                    record.installation_id,
                    record.instance_id,
                ),
            )
            for ordinal, artifact_id in enumerate(record.artifact_ids, start=1):
                connection.execute(
                    """
                    INSERT INTO lifecycle_test_artifacts(
                        test_id, ordinal, artifact_id
                    ) VALUES (?, ?, ?)
                    """,
                    (record.test_id, ordinal, artifact_id),
                )

        for record in sorted(
            repository.failures.values(), key=lambda item: item.failure_id
        ):
            connection.execute(
                """
                INSERT INTO lifecycle_failures(
                    failure_id, revision_id, failed_at, failure_type,
                    damage_location, circumstances, manufacturing_id,
                    installation_id, estimated_cause, confirmed_cause,
                    related_feature, instance_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.failure_id,
                    record.revision_id,
                    record.failed_at.isoformat(),
                    record.failure_type,
                    record.damage_location,
                    record.circumstances,
                    record.manufacturing_id,
                    record.installation_id,
                    record.estimated_cause,
                    record.confirmed_cause,
                    record.related_feature,
                    record.instance_id,
                ),
            )
            for ordinal, artifact_id in enumerate(
                record.evidence_artifact_ids, start=1
            ):
                connection.execute(
                    """
                    INSERT INTO lifecycle_failure_evidence(
                        failure_id, ordinal, artifact_id
                    ) VALUES (?, ?, ?)
                    """,
                    (record.failure_id, ordinal, artifact_id),
                )

        for event in sorted(repository.events, key=lambda item: item.sequence):
            connection.execute(
                """
                INSERT INTO lifecycle_events_relational(
                    event_id, event_type, occurred_at, sequence, revision_id,
                    manufacturing_id, installation_id, test_id, failure_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.occurred_at.isoformat(),
                    event.sequence,
                    event.revision_id,
                    event.manufacturing_id,
                    event.installation_id,
                    event.test_id,
                    event.failure_id,
                ),
            )

        for event in sorted(
            repository.physical_events, key=lambda item: item.sequence
        ):
            connection.execute(
                """
                INSERT INTO lifecycle_physical_events_relational(
                    event_id, event_type, occurred_at, sequence, instance_id,
                    revision_id, manufacturing_id, installation_id, test_id,
                    failure_id, equipment_id, position, test_outcome,
                    replacement_instance_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.occurred_at.isoformat(),
                    event.sequence,
                    event.instance_id,
                    event.revision_id,
                    event.manufacturing_id,
                    event.installation_id,
                    event.test_id,
                    event.failure_id,
                    event.equipment_id,
                    event.position,
                    event.test_outcome.value if event.test_outcome is not None else None,
                    event.replacement_instance_id,
                    event.notes,
                ),
            )


class SQLiteLifecycleQueryRepository:
    """SQL-native committed-state queries for lifecycle engineering knowledge."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def revision_history(self, part_id: str) -> tuple[RevisionQueryResult, ...]:
        rows = self.connection.execute(
            """
            SELECT revision_id, part_id, revision_code, created_at,
                   origin, verification_status, runtime_status,
                   runtime_evidence_schema_version, runtime_real_host_executed
            FROM lifecycle_revisions
            WHERE part_id = ?
            ORDER BY created_at, revision_id
            """,
            (part_id,),
        ).fetchall()
        return tuple(
            RevisionQueryResult(
                revision_id=row[0],
                part_id=row[1],
                revision_code=row[2],
                created_at=datetime.fromisoformat(row[3]),
                origin=row[4],
                verification_status=row[5],
                runtime_status=row[6],
                runtime_evidence_schema_version=row[7],
                runtime_real_host_executed=(
                    bool(row[8]) if row[8] is not None else None
                ),
            )
            for row in rows
        )

    def failure_history(
        self,
        *,
        revision_id: Optional[str] = None,
        instance_id: Optional[str] = None,
    ) -> tuple[FailureQueryResult, ...]:
        if revision_id is None and instance_id is None:
            raise ValueError("revision_id or instance_id is required")

        clauses: list[str] = []
        parameters: list[str] = []
        if revision_id is not None:
            clauses.append("f.revision_id = ?")
            parameters.append(revision_id)
        if instance_id is not None:
            clauses.append("f.instance_id = ?")
            parameters.append(instance_id)

        rows = self.connection.execute(
            f"""
            SELECT f.failure_id, f.revision_id, f.instance_id, f.failed_at,
                   f.failure_type, f.damage_location, f.confirmed_cause,
                   i.equipment_id, i.position
            FROM lifecycle_failures AS f
            LEFT JOIN lifecycle_installations AS i
                   ON i.installation_id = f.installation_id
            WHERE {' AND '.join(clauses)}
            ORDER BY f.failed_at, f.failure_id
            """,
            tuple(parameters),
        ).fetchall()
        return tuple(
            FailureQueryResult(
                failure_id=row[0],
                revision_id=row[1],
                instance_id=row[2],
                failed_at=datetime.fromisoformat(row[3]),
                failure_type=row[4],
                damage_location=row[5],
                confirmed_cause=row[6],
                equipment_id=row[7],
                position=row[8],
            )
            for row in rows
        )

    def equipment_occupancy(
        self,
        *,
        equipment_id: str,
        position: Optional[str] = None,
    ) -> tuple[EquipmentOccupancyQueryResult, ...]:
        position_clause = ""
        parameters: list[str] = [equipment_id]
        if position is not None:
            position_clause = "AND p.position = ?"
            parameters.append(position)

        rows = self.connection.execute(
            f"""
            WITH latest AS (
                SELECT instance_id, MAX(sequence) AS max_sequence
                FROM lifecycle_physical_events_relational
                GROUP BY instance_id
            )
            SELECT p.instance_id, i.part_id, p.revision_id,
                   p.manufacturing_id, p.equipment_id, p.position,
                   p.event_type, p.occurred_at
            FROM lifecycle_physical_events_relational AS p
            JOIN latest AS l
              ON l.instance_id = p.instance_id
             AND l.max_sequence = p.sequence
            JOIN lifecycle_physical_instances AS i
              ON i.instance_id = p.instance_id
            WHERE p.equipment_id = ?
              {position_clause}
              AND p.event_type IN ('INSTALLED', 'TESTED', 'ACTIVATED', 'FAILED')
            ORDER BY p.position, p.instance_id
            """,
            tuple(parameters),
        ).fetchall()

        return tuple(
            EquipmentOccupancyQueryResult(
                instance_id=row[0],
                part_id=row[1],
                revision_id=row[2],
                manufacturing_id=row[3],
                equipment_id=row[4],
                position=row[5],
                state="ACTIVE" if row[6] == "ACTIVATED" else row[6],
                occurred_at=datetime.fromisoformat(row[7]),
            )
            for row in rows
        )

    def physical_timeline(
        self, instance_id: str
    ) -> tuple[PhysicalEventQueryResult, ...]:
        rows = self.connection.execute(
            """
            SELECT event_id, event_type, occurred_at, sequence, instance_id,
                   revision_id, manufacturing_id, installation_id, test_id,
                   failure_id, equipment_id, position, test_outcome,
                   replacement_instance_id, notes
            FROM lifecycle_physical_events_relational
            WHERE instance_id = ?
            ORDER BY sequence
            """,
            (instance_id,),
        ).fetchall()
        return tuple(
            PhysicalEventQueryResult(
                event_id=row[0],
                event_type=row[1],
                occurred_at=datetime.fromisoformat(row[2]),
                sequence=int(row[3]),
                instance_id=row[4],
                revision_id=row[5],
                manufacturing_id=row[6],
                installation_id=row[7],
                test_id=row[8],
                failure_id=row[9],
                equipment_id=row[10],
                position=row[11],
                test_outcome=row[12],
                replacement_instance_id=row[13],
                notes=row[14],
            )
            for row in rows
        )
