from __future__ import annotations

from typing import Optional

from .engineering_knowledge import (
    EquipmentPositionHistoryEntry,
    FailurePatternSummary,
    RevisionOutcomeSummary,
    SQLiteEngineeringKnowledgeRepository,
)
from .knowledge_paging import (
    DEFAULT_KNOWLEDGE_PAGE_LIMIT,
    KnowledgeCursorState,
    KnowledgeKeysetCursorState,
    KnowledgePage,
    LifecycleKnowledgeCursorError,
    decode_knowledge_keyset_cursor,
    encode_knowledge_keyset_cursor,
    page_from_rows,
    query_fingerprint,
    validate_page_limit,
)


class SQLiteKeysetEngineeringKnowledgeRepository(SQLiteEngineeringKnowledgeRepository):
    """Keyset paging for factual lifecycle histories and grouped failure patterns.

    New traversals emit v2 keyset cursors. Already-issued v1 offset cursors remain
    accepted and stay on their historical OFFSET execution paths so an in-flight
    traversal is not silently reinterpreted after upgrade.
    """

    def _paging_state(
        self,
        *,
        query_name: str,
        filters: dict[str, object],
        cursor: Optional[str],
    ) -> tuple[str, KnowledgeKeysetCursorState | KnowledgeCursorState | None]:
        fingerprint = query_fingerprint(query_name, filters)
        if cursor is None:
            return fingerprint, None
        return (
            fingerprint,
            decode_knowledge_keyset_cursor(
                cursor,
                expected_query_fingerprint=fingerprint,
                expected_snapshot_version=self.snapshot_version,
            ),
        )

    def revision_outcomes_page(
        self,
        part_id: str,
        *,
        limit: int = DEFAULT_KNOWLEDGE_PAGE_LIMIT,
        cursor: Optional[str] = None,
    ) -> KnowledgePage[RevisionOutcomeSummary]:
        page_limit = validate_page_limit(limit)
        fingerprint, state = self._paging_state(
            query_name="revision_outcomes_page",
            filters={"part_id": part_id},
            cursor=cursor,
        )

        if isinstance(state, KnowledgeCursorState):
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
                (part_id, page_limit + 1, state.offset),
            ).fetchall()
            return page_from_rows(
                tuple(self._revision_outcome(row) for row in rows),
                limit=page_limit,
                offset=state.offset,
                query_fingerprint_value=fingerprint,
                snapshot_version=self.snapshot_version,
            )

        clauses = ["r.part_id = ?"]
        parameters: list[object] = [part_id]
        if isinstance(state, KnowledgeKeysetCursorState):
            if (
                len(state.key) != 2
                or not isinstance(state.key[0], str)
                or not isinstance(state.key[1], str)
            ):
                raise LifecycleKnowledgeCursorError(
                    "invalid revision-outcomes keyset cursor"
                )
            created_at, revision_id = state.key
            clauses.append(
                "(r.created_at > ? OR (r.created_at = ? AND r.revision_id > ?))"
            )
            parameters.extend((created_at, created_at, revision_id))
        parameters.append(page_limit + 1)

        rows = self.connection.execute(
            f"""
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
                   COUNT(DISTINCT f.failure_id) AS failure_records,
                   r.created_at
            FROM lifecycle_revisions AS r
            LEFT JOIN lifecycle_manufacturing AS m
                   ON m.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_instances AS pi
                   ON pi.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_events_relational AS pe
                   ON pe.instance_id = pi.instance_id
            LEFT JOIN lifecycle_failures AS f
                   ON f.revision_id = r.revision_id
            WHERE {' AND '.join(clauses)}
            GROUP BY r.revision_id, r.revision_code, r.created_at
            ORDER BY r.created_at, r.revision_id
            LIMIT ?
            """,
            tuple(parameters),
        ).fetchall()
        visible_rows = rows[:page_limit]
        next_cursor = None
        if len(rows) > page_limit and visible_rows:
            last = visible_rows[-1]
            next_cursor = encode_knowledge_keyset_cursor(
                query_fingerprint_value=fingerprint,
                snapshot_version=self.snapshot_version,
                key=(str(last[9]), str(last[0])),
            )
        return KnowledgePage(
            items=tuple(self._revision_outcome(row[:9]) for row in visible_rows),
            next_cursor=next_cursor,
            snapshot_version=self.snapshot_version,
        )

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
        fingerprint, state = self._paging_state(
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

        if isinstance(state, KnowledgeCursorState):
            parameters.extend((page_limit + 1, state.offset))
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
                offset=state.offset,
                query_fingerprint_value=fingerprint,
                snapshot_version=self.snapshot_version,
            )

        if isinstance(state, KnowledgeKeysetCursorState):
            if (
                len(state.key) != 3
                or not isinstance(state.key[0], str)
                or isinstance(state.key[1], bool)
                or not isinstance(state.key[1], int)
                or not isinstance(state.key[2], str)
            ):
                raise LifecycleKnowledgeCursorError(
                    "invalid equipment-history keyset cursor"
                )
            occurred_at, sequence, event_id = state.key
            clauses.append(
                "(pe.occurred_at > ? OR "
                "(pe.occurred_at = ? AND (pe.sequence > ? OR "
                "(pe.sequence = ? AND pe.event_id > ?))))"
            )
            parameters.extend(
                (occurred_at, occurred_at, sequence, sequence, event_id)
            )
        parameters.append(page_limit + 1)

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
            LIMIT ?
            """,
            tuple(parameters),
        ).fetchall()
        visible_rows = rows[:page_limit]
        next_cursor = None
        if len(rows) > page_limit and visible_rows:
            last = visible_rows[-1]
            next_cursor = encode_knowledge_keyset_cursor(
                query_fingerprint_value=fingerprint,
                snapshot_version=self.snapshot_version,
                key=(str(last[2]), int(last[3]), str(last[0])),
            )
        return KnowledgePage(
            items=tuple(self._equipment_history_entry(row) for row in visible_rows),
            next_cursor=next_cursor,
            snapshot_version=self.snapshot_version,
        )

    def failure_patterns_page(
        self,
        *,
        part_id: Optional[str] = None,
        revision_id: Optional[str] = None,
        limit: int = DEFAULT_KNOWLEDGE_PAGE_LIMIT,
        cursor: Optional[str] = None,
    ) -> KnowledgePage[FailurePatternSummary]:
        """Page grouped failure patterns with aggregate-aware keyset continuation.

        The primary sort key is the derived occurrence count in descending order.
        New v2 traversals therefore continue with an outer CTE predicate over the
        grouped result. A null-rank plus normalized cause string provide a total
        deterministic tie-break without changing the factual grouping itself.
        """
        page_limit = validate_page_limit(limit)
        filters = {"part_id": part_id, "revision_id": revision_id}
        fingerprint, state = self._paging_state(
            query_name="failure_patterns_page",
            filters=filters,
            cursor=cursor,
        )

        clauses: list[str] = []
        filter_parameters: list[object] = []
        if part_id is not None:
            clauses.append("r.part_id = ?")
            filter_parameters.append(part_id)
        if revision_id is not None:
            clauses.append("f.revision_id = ?")
            filter_parameters.append(revision_id)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        if isinstance(state, KnowledgeCursorState):
            # Preserve the exact historical v1 ordering/execution contract for an
            # already-issued offset cursor. New traversals never enter this path.
            parameters = [*filter_parameters, page_limit + 1, state.offset]
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
                offset=state.offset,
                query_fingerprint_value=fingerprint,
                snapshot_version=self.snapshot_version,
            )

        continuation_clause = ""
        continuation_parameters: list[object] = []
        if isinstance(state, KnowledgeKeysetCursorState):
            if (
                len(state.key) != 5
                or isinstance(state.key[0], bool)
                or not isinstance(state.key[0], int)
                or not isinstance(state.key[1], str)
                or not isinstance(state.key[2], str)
                or isinstance(state.key[3], bool)
                or not isinstance(state.key[3], int)
                or state.key[3] not in (0, 1)
                or not isinstance(state.key[4], str)
            ):
                raise LifecycleKnowledgeCursorError(
                    "invalid failure-pattern keyset cursor"
                )
            (
                occurrence_count,
                failure_type,
                damage_location,
                cause_null_rank,
                cause_sort,
            ) = state.key
            continuation_clause = """
            WHERE occurrence_count < ?
               OR (occurrence_count = ? AND failure_type > ?)
               OR (occurrence_count = ? AND failure_type = ?
                   AND damage_location > ?)
               OR (occurrence_count = ? AND failure_type = ?
                   AND damage_location = ? AND cause_null_rank > ?)
               OR (occurrence_count = ? AND failure_type = ?
                   AND damage_location = ? AND cause_null_rank = ?
                   AND cause_sort > ?)
            """
            continuation_parameters.extend(
                (
                    occurrence_count,
                    occurrence_count,
                    failure_type,
                    occurrence_count,
                    failure_type,
                    damage_location,
                    occurrence_count,
                    failure_type,
                    damage_location,
                    cause_null_rank,
                    occurrence_count,
                    failure_type,
                    damage_location,
                    cause_null_rank,
                    cause_sort,
                )
            )

        parameters = [
            *filter_parameters,
            *continuation_parameters,
            page_limit + 1,
        ]
        rows = self.connection.execute(
            f"""
            WITH patterns AS (
                SELECT f.failure_type AS failure_type,
                       f.damage_location AS damage_location,
                       f.confirmed_cause AS confirmed_cause,
                       COUNT(*) AS occurrence_count,
                       COUNT(DISTINCT f.revision_id) AS revision_count,
                       COUNT(DISTINCT f.instance_id) AS instance_count,
                       MIN(f.failed_at) AS first_failed_at,
                       MAX(f.failed_at) AS last_failed_at,
                       CASE WHEN f.confirmed_cause IS NULL THEN 0 ELSE 1 END
                           AS cause_null_rank,
                       COALESCE(f.confirmed_cause, '') AS cause_sort
                FROM lifecycle_failures AS f
                JOIN lifecycle_revisions AS r
                  ON r.revision_id = f.revision_id
                {where_clause}
                GROUP BY f.failure_type, f.damage_location, f.confirmed_cause
            )
            SELECT failure_type,
                   damage_location,
                   confirmed_cause,
                   occurrence_count,
                   revision_count,
                   instance_count,
                   first_failed_at,
                   last_failed_at,
                   cause_null_rank,
                   cause_sort
            FROM patterns
            {continuation_clause}
            ORDER BY occurrence_count DESC,
                     failure_type,
                     damage_location,
                     cause_null_rank,
                     cause_sort
            LIMIT ?
            """,
            tuple(parameters),
        ).fetchall()

        visible_rows = rows[:page_limit]
        next_cursor = None
        if len(rows) > page_limit and visible_rows:
            last = visible_rows[-1]
            next_cursor = encode_knowledge_keyset_cursor(
                query_fingerprint_value=fingerprint,
                snapshot_version=self.snapshot_version,
                key=(
                    int(last[3]),
                    str(last[0]),
                    str(last[1]),
                    int(last[8]),
                    str(last[9]),
                ),
            )
        return KnowledgePage(
            items=tuple(self._failure_pattern(row[:8]) for row in visible_rows),
            next_cursor=next_cursor,
            snapshot_version=self.snapshot_version,
        )
