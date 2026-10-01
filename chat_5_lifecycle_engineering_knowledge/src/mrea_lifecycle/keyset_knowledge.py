from __future__ import annotations

from typing import Optional

from .engineering_knowledge import (
    EquipmentPositionHistoryEntry,
    RevisionOutcomeSummary,
    SQLiteEngineeringKnowledgeRepository,
)
from .knowledge_paging import (
    DEFAULT_KNOWLEDGE_PAGE_LIMIT,
    KnowledgeCursorState,
    KnowledgeKeysetCursorState,
    KnowledgePage,
    decode_knowledge_keyset_cursor,
    encode_knowledge_keyset_cursor,
    page_from_rows,
    query_fingerprint,
    validate_page_limit,
)


class SQLiteKeysetEngineeringKnowledgeRepository(SQLiteEngineeringKnowledgeRepository):
    """Pass-10.1 keyset paging for high-cardinality factual history queries.

    Existing tuple queries and aggregate failure-pattern paging stay inherited from
    Pass 7-8. Revision outcomes and equipment history emit v2 keyset cursors, while
    already-issued v1 offset cursors remain accepted for traversal continuity.
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
                from .knowledge_paging import LifecycleKnowledgeCursorError

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
                from .knowledge_paging import LifecycleKnowledgeCursorError

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
