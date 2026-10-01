from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sqlite3
from typing import Optional

from .knowledge_paging import (
    DEFAULT_KNOWLEDGE_PAGE_LIMIT,
    KnowledgePage,
    decode_knowledge_cursor,
    page_from_rows,
    query_fingerprint,
    validate_page_limit,
)


class LifecycleKnowledgeIntegrityError(RuntimeError):
    """Raised when committed lifecycle facts cannot form a deterministic projection."""


@dataclass(frozen=True, slots=True)
class RevisionLineageEntry:
    revision_id: str
    part_id: str
    revision_code: str
    parent_revision_id: Optional[str]
    created_at: datetime
    depth: int


@dataclass(frozen=True, slots=True)
class RevisionOutcomeSummary:
    revision_id: str
    revision_code: str
    manufacturing_records: int
    physical_instances: int
    activated_instances: int
    failed_instances: int
    removed_instances: int
    superseded_instances: int
    failure_records: int


@dataclass(frozen=True, slots=True)
class EquipmentPositionHistoryEntry:
    event_id: str
    event_type: str
    occurred_at: datetime
    sequence: int
    instance_id: str
    part_id: str
    revision_id: str
    manufacturing_id: str
    equipment_id: str
    position: str
    replacement_instance_id: Optional[str]
    notes: Optional[str]


@dataclass(frozen=True, slots=True)
class FailurePatternSummary:
    failure_type: str
    damage_location: str
    confirmed_cause: Optional[str]
    occurrence_count: int
    revision_count: int
    instance_count: int
    first_failed_at: datetime
    last_failed_at: datetime


@dataclass(frozen=True, slots=True)
class ReplacementChainEntry:
    instance_id: str
    revision_id: str
    manufacturing_id: str
    state: str
    replacement_instance_id: Optional[str]


_STATE_BY_EVENT = {
    "MANUFACTURED": "MANUFACTURED",
    "INSTALLED": "INSTALLED",
    "TESTED": "TESTED",
    "ACTIVATED": "ACTIVE",
    "FAILED": "FAILED",
    "REMOVED": "REMOVED",
    "SUPERSEDED": "SUPERSEDED",
}


class SQLiteEngineeringKnowledgeRepository:
    """Deterministic factual engineering knowledge queries over committed SQL facts.

    The repository deliberately returns counts, lineage and event relationships only.
    It does not infer causality, quality rankings, recommendations or AI conclusions.
    Paginated queries use opaque cursors bound to this committed snapshot version.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        snapshot_version: int = 0,
    ) -> None:
        self.connection = connection
        self.snapshot_version = snapshot_version

    def _page_offset(
        self,
        *,
        query_name: str,
        filters: dict[str, object],
        cursor: Optional[str],
    ) -> tuple[str, int]:
        fingerprint = query_fingerprint(query_name, filters)
        if cursor is None:
            return fingerprint, 0
        state = decode_knowledge_cursor(
            cursor,
            expected_query_fingerprint=fingerprint,
            expected_snapshot_version=self.snapshot_version,
        )
        return fingerprint, state.offset

    def revision_lineage(self, part_id: str) -> tuple[RevisionLineageEntry, ...]:
        rows = self.connection.execute(
            """
            SELECT revision_id, part_id, revision_code,
                   parent_revision_id, created_at
            FROM lifecycle_revisions
            WHERE part_id = ?
            ORDER BY created_at, revision_id
            """,
            (part_id,),
        ).fetchall()
        if not rows:
            return ()

        raw = {
            str(row[0]): {
                "revision_id": str(row[0]),
                "part_id": str(row[1]),
                "revision_code": str(row[2]),
                "parent_revision_id": row[3],
                "created_at": datetime.fromisoformat(row[4]),
            }
            for row in rows
        }
        depths: dict[str, int] = {}
        visiting: set[str] = set()

        def depth_for(revision_id: str) -> int:
            known = depths.get(revision_id)
            if known is not None:
                return known
            if revision_id in visiting:
                raise LifecycleKnowledgeIntegrityError(
                    f"revision lineage cycle detected at {revision_id}"
                )
            visiting.add(revision_id)
            parent_id = raw[revision_id]["parent_revision_id"]
            if parent_id is None:
                depth = 0
            else:
                parent_key = str(parent_id)
                if parent_key not in raw:
                    raise LifecycleKnowledgeIntegrityError(
                        "revision lineage references a missing parent: "
                        f"{revision_id} -> {parent_key}"
                    )
                depth = depth_for(parent_key) + 1
            visiting.remove(revision_id)
            depths[revision_id] = depth
            return depth

        entries = tuple(
            RevisionLineageEntry(
                revision_id=revision_id,
                part_id=str(item["part_id"]),
                revision_code=str(item["revision_code"]),
                parent_revision_id=(
                    str(item["parent_revision_id"])
                    if item["parent_revision_id"] is not None
                    else None
                ),
                created_at=item["created_at"],  # type: ignore[arg-type]
                depth=depth_for(revision_id),
            )
            for revision_id, item in raw.items()
        )
        return tuple(
            sorted(
                entries,
                key=lambda item: (item.depth, item.created_at, item.revision_id),
            )
        )

    def revision_outcomes(
        self, part_id: str
    ) -> tuple[RevisionOutcomeSummary, ...]:
        rows = self.connection.execute(
            """
            SELECT r.revision_id,
                   r.revision_code,
                   COUNT(DISTINCT m.manufacturing_id) AS manufacturing_records,
                   COUNT(DISTINCT pi.instance_id) AS physical_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'ACTIVATED'
                                       THEN pe.instance_id END) AS activated_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'FAILED'
                                       THEN pe.instance_id END) AS failed_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'REMOVED'
                                       THEN pe.instance_id END) AS removed_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'SUPERSEDED'
                                       THEN pe.instance_id END) AS superseded_instances,
                   COUNT(DISTINCT f.failure_id) AS failure_records
            FROM lifecycle_revisions AS r
            LEFT JOIN lifecycle_manufacturing AS m
                   ON m.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_instances AS pi
                   ON pi.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_events_relational AS pe
                   ON pe.instance_id = pi.instance_id
            LEFT JOIN lifecycle_failures AS f
                   ON f.revision_id = r.revision_id
            WHERE r.part_id = ?
            GROUP BY r.revision_id, r.revision_code, r.created_at
            ORDER BY r.created_at, r.revision_id
            """,
            (part_id,),
        ).fetchall()
        return tuple(self._revision_outcome(row) for row in rows)

    def revision_outcomes_page(
        self,
        part_id: str,
        *,
        limit: int = DEFAULT_KNOWLEDGE_PAGE_LIMIT,
        cursor: Optional[str] = None,
    ) -> KnowledgePage[RevisionOutcomeSummary]:
        page_limit = validate_page_limit(limit)
        fingerprint, offset = self._page_offset(
            query_name="revision_outcomes_page",
            filters={"part_id": part_id},
            cursor=cursor,
        )
        rows = self.connection.execute(
            """
            SELECT r.revision_id,
                   r.revision_code,
                   COUNT(DISTINCT m.manufacturing_id) AS manufacturing_records,
                   COUNT(DISTINCT pi.instance_id) AS physical_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'ACTIVATED'
                                       THEN pe.instance_id END) AS activated_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'FAILED'
                                       THEN pe.instance_id END) AS failed_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'REMOVED'
                                       THEN pe.instance_id END) AS removed_instances,
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'SUPERSEDED'
                                       THEN pe.instance_id END) AS superseded_instances,
                   COUNT(DISTINCT f.failure_id) AS failure_records
            FROM lifecycle_revisions AS r
            LEFT JOIN lifecycle_manufacturing AS m
                   ON m.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_instances AS pi
                   ON pi.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_events_relational AS pe
                   ON pe.instance_id = pi.instance_id
            LEFT JOIN lifecycle_failures AS f
                   ON f.revision_id = r.revision_id
            WHERE r.part_id = ?
            GROUP BY r.revision_id, r.revision_code, r.created_at
            ORDER BY r.created_at, r.revision_id
            LIMIT ? OFFSET ?
            """,
            (part_id, page_limit + 1, offset),
        ).fetchall()
        return page_from_rows(
            tuple(self._revision_outcome(row) for row in rows),
            limit=page_limit,
            offset=offset,
            query_fingerprint_value=fingerprint,
            snapshot_version=self.snapshot_version,
        )

    @staticmethod
    def _revision_outcome(row: tuple[object, ...]) -> RevisionOutcomeSummary:
        return RevisionOutcomeSummary(
            revision_id=str(row[0]),
            revision_code=str(row[1]),
            manufacturing_records=int(row[2]),
            physical_instances=int(row[3]),
            activated_instances=int(row[4]),
            failed_instances=int(row[5]),
            removed_instances=int(row[6]),
            superseded_instances=int(row[7]),
            failure_records=int(row[8]),
        )

    def equipment_position_history(
        self,
        *,
        equipment_id: str,
        position: Optional[str] = None,
    ) -> tuple[EquipmentPositionHistoryEntry, ...]:
        clauses = ["pe.equipment_id = ?"]
        parameters: list[object] = [equipment_id]
        if position is not None:
            clauses.append("pe.position = ?")
            parameters.append(position)

        rows = self.connection.execute(
            f"""
            SELECT pe.event_id, pe.event_type, pe.occurred_at, pe.sequence,
                   pe.instance_id, pi.part_id, pe.revision_id,
                   pe.manufacturing_id, pe.equipment_id, pe.position,
                   pe.replacement_instance_id, pe.notes
            FROM lifecycle_physical_events_relational AS pe
            JOIN lifecycle_physical_instances AS pi
              ON pi.instance_id = pe.instance_id
            WHERE {' AND '.join(clauses)}
            ORDER BY pe.occurred_at, pe.sequence, pe.event_id
            """,
            tuple(parameters),
        ).fetchall()
        return tuple(self._equipment_history_entry(row) for row in rows)

    def equipment_position_history_page(
        self,
        *,
        equipment_id: str,
        position: Optional[str] = None,
        event_type: Optional[str] = None,
        revision_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        limit: int = DEFAULT_KNOWLEDGE_PAGE_LIMIT,
        cursor: Optional[str] = None,
    ) -> KnowledgePage[EquipmentPositionHistoryEntry]:
        page_limit = validate_page_limit(limit)
        filters = {
            "equipment_id": equipment_id,
            "position": position,
            "event_type": event_type,
            "revision_id": revision_id,
            "instance_id": instance_id,
        }
        fingerprint, offset = self._page_offset(
            query_name="equipment_position_history_page",
            filters=filters,
            cursor=cursor,
        )
        clauses = ["pe.equipment_id = ?"]
        parameters: list[object] = [equipment_id]
        for column, value in (
            ("pe.position", position),
            ("pe.event_type", event_type),
            ("pe.revision_id", revision_id),
            ("pe.instance_id", instance_id),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        parameters.extend((page_limit + 1, offset))

        rows = self.connection.execute(
            f"""
            SELECT pe.event_id, pe.event_type, pe.occurred_at, pe.sequence,
                   pe.instance_id, pi.part_id, pe.revision_id,
                   pe.manufacturing_id, pe.equipment_id, pe.position,
                   pe.replacement_instance_id, pe.notes
            FROM lifecycle_physical_events_relational AS pe
            JOIN lifecycle_physical_instances AS pi
              ON pi.instance_id = pe.instance_id
            WHERE {' AND '.join(clauses)}
            ORDER BY pe.occurred_at, pe.sequence, pe.event_id
            LIMIT ? OFFSET ?
            """,
            tuple(parameters),
        ).fetchall()
        return page_from_rows(
            tuple(self._equipment_history_entry(row) for row in rows),
            limit=page_limit,
            offset=offset,
            query_fingerprint_value=fingerprint,
            snapshot_version=self.snapshot_version,
        )

    @staticmethod
    def _equipment_history_entry(
        row: tuple[object, ...],
    ) -> EquipmentPositionHistoryEntry:
        return EquipmentPositionHistoryEntry(
            event_id=str(row[0]),
            event_type=str(row[1]),
            occurred_at=datetime.fromisoformat(str(row[2])),
            sequence=int(row[3]),
            instance_id=str(row[4]),
            part_id=str(row[5]),
            revision_id=str(row[6]),
            manufacturing_id=str(row[7]),
            equipment_id=str(row[8]),
            position=str(row[9]),
            replacement_instance_id=(str(row[10]) if row[10] is not None else None),
            notes=(str(row[11]) if row[11] is not None else None),
        )

    def failure_patterns(
        self,
        *,
        part_id: Optional[str] = None,
        revision_id: Optional[str] = None,
    ) -> tuple[FailurePatternSummary, ...]:
        clauses: list[str] = []
        parameters: list[object] = []
        if part_id is not None:
            clauses.append("r.part_id = ?")
            parameters.append(part_id)
        if revision_id is not None:
            clauses.append("f.revision_id = ?")
            parameters.append(revision_id)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.connection.execute(
            f"""
            SELECT f.failure_type,
                   f.damage_location,
                   f.confirmed_cause,
                   COUNT(*) AS occurrence_count,
                   COUNT(DISTINCT f.revision_id) AS revision_count,
                   COUNT(DISTINCT f.instance_id) AS instance_count,
                   MIN(f.failed_at) AS first_failed_at,
                   MAX(f.failed_at) AS last_failed_at
            FROM lifecycle_failures AS f
            JOIN lifecycle_revisions AS r
              ON r.revision_id = f.revision_id
            {where_clause}
            GROUP BY f.failure_type, f.damage_location, f.confirmed_cause
            ORDER BY occurrence_count DESC,
                     f.failure_type,
                     f.damage_location,
                     COALESCE(f.confirmed_cause, '')
            """,
            tuple(parameters),
        ).fetchall()
        return tuple(self._failure_pattern(row) for row in rows)

    def failure_patterns_page(
        self,
        *,
        part_id: Optional[str] = None,
        revision_id: Optional[str] = None,
        limit: int = DEFAULT_KNOWLEDGE_PAGE_LIMIT,
        cursor: Optional[str] = None,
    ) -> KnowledgePage[FailurePatternSummary]:
        page_limit = validate_page_limit(limit)
        fingerprint, offset = self._page_offset(
            query_name="failure_patterns_page",
            filters={"part_id": part_id, "revision_id": revision_id},
            cursor=cursor,
        )
        clauses: list[str] = []
        parameters: list[object] = []
        if part_id is not None:
            clauses.append("r.part_id = ?")
            parameters.append(part_id)
        if revision_id is not None:
            clauses.append("f.revision_id = ?")
            parameters.append(revision_id)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.extend((page_limit + 1, offset))

        rows = self.connection.execute(
            f"""
            SELECT f.failure_type,
                   f.damage_location,
                   f.confirmed_cause,
                   COUNT(*) AS occurrence_count,
                   COUNT(DISTINCT f.revision_id) AS revision_count,
                   COUNT(DISTINCT f.instance_id) AS instance_count,
                   MIN(f.failed_at) AS first_failed_at,
                   MAX(f.failed_at) AS last_failed_at
            FROM lifecycle_failures AS f
            JOIN lifecycle_revisions AS r
              ON r.revision_id = f.revision_id
            {where_clause}
            GROUP BY f.failure_type, f.damage_location, f.confirmed_cause
            ORDER BY occurrence_count DESC,
                     f.failure_type,
                     f.damage_location,
                     COALESCE(f.confirmed_cause, '')
            LIMIT ? OFFSET ?
            """,
            tuple(parameters),
        ).fetchall()
        return page_from_rows(
            tuple(self._failure_pattern(row) for row in rows),
            limit=page_limit,
            offset=offset,
            query_fingerprint_value=fingerprint,
            snapshot_version=self.snapshot_version,
        )

    @staticmethod
    def _failure_pattern(row: tuple[object, ...]) -> FailurePatternSummary:
        return FailurePatternSummary(
            failure_type=str(row[0]),
            damage_location=str(row[1]),
            confirmed_cause=(str(row[2]) if row[2] is not None else None),
            occurrence_count=int(row[3]),
            revision_count=int(row[4]),
            instance_count=int(row[5]),
            first_failed_at=datetime.fromisoformat(str(row[6])),
            last_failed_at=datetime.fromisoformat(str(row[7])),
        )

    def replacement_chain(
        self, instance_id: str
    ) -> tuple[ReplacementChainEntry, ...]:
        exists = self.connection.execute(
            """
            SELECT 1
            FROM lifecycle_physical_instances
            WHERE instance_id = ?
            """,
            (instance_id,),
        ).fetchone()
        if exists is None:
            return ()

        chain: list[ReplacementChainEntry] = []
        seen: set[str] = set()
        current = instance_id
        while current is not None:
            if current in seen:
                raise LifecycleKnowledgeIntegrityError(
                    f"replacement cycle detected at {current}"
                )
            seen.add(current)

            identity = self.connection.execute(
                """
                SELECT revision_id, manufacturing_id
                FROM lifecycle_physical_instances
                WHERE instance_id = ?
                """,
                (current,),
            ).fetchone()
            if identity is None:
                raise LifecycleKnowledgeIntegrityError(
                    f"replacement chain references missing instance: {current}"
                )

            latest = self.connection.execute(
                """
                SELECT event_type
                FROM lifecycle_physical_events_relational
                WHERE instance_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (current,),
            ).fetchone()
            if latest is None or latest[0] not in _STATE_BY_EVENT:
                raise LifecycleKnowledgeIntegrityError(
                    f"instance has no valid physical state: {current}"
                )

            superseded = self.connection.execute(
                """
                SELECT replacement_instance_id
                FROM lifecycle_physical_events_relational
                WHERE instance_id = ?
                  AND event_type = 'SUPERSEDED'
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (current,),
            ).fetchone()
            replacement = superseded[0] if superseded is not None else None
            chain.append(
                ReplacementChainEntry(
                    instance_id=current,
                    revision_id=identity[0],
                    manufacturing_id=identity[1],
                    state=_STATE_BY_EVENT[latest[0]],
                    replacement_instance_id=replacement,
                )
            )
            current = replacement

        return tuple(chain)
