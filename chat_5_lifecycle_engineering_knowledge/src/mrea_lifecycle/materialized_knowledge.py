from __future__ import annotations

from typing import Optional

from .engineering_knowledge import FailurePatternSummary, RevisionOutcomeSummary
from .keyset_knowledge import SQLiteKeysetEngineeringKnowledgeRepository
from .knowledge_paging import (
    DEFAULT_KNOWLEDGE_PAGE_LIMIT,
    KnowledgeCursorState,
    KnowledgeKeysetCursorState,
    KnowledgePage,
    LifecycleKnowledgeCursorError,
    encode_knowledge_keyset_cursor,
    validate_page_limit,
)


class SQLiteMaterializedEngineeringKnowledgeRepository(
    SQLiteKeysetEngineeringKnowledgeRepository
):
    """Snapshot-bound knowledge queries backed by materialized aggregate tables.

    Revision outcomes and failure-pattern summaries are precomputed as part of the
    relational read-model commit. New v2 traversals therefore read already-grouped
    rows. Legacy v1 cursors deliberately delegate to the historical raw OFFSET path
    so already-issued cursors keep their original execution semantics.
    """

    def revision_outcomes(
        self, part_id: str
    ) -> tuple[RevisionOutcomeSummary, ...]:
        rows = self.connection.execute(
            """
            SELECT revision_id,
                   revision_code,
                   manufacturing_records,
                   physical_instances,
                   activated_instances,
                   failed_instances,
                   removed_instances,
                   superseded_instances,
                   failure_records
            FROM lifecycle_revision_outcomes_materialized
            WHERE part_id = ?
            ORDER BY created_at, revision_id
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
        fingerprint, state = self._paging_state(
            query_name="revision_outcomes_page",
            filters={"part_id": part_id},
            cursor=cursor,
        )
        if isinstance(state, KnowledgeCursorState):
            return super().revision_outcomes_page(
                part_id,
                limit=page_limit,
                cursor=cursor,
            )

        clauses = ["part_id = ?"]
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
                "(created_at > ? OR (created_at = ? AND revision_id > ?))"
            )
            parameters.extend((created_at, created_at, revision_id))
        parameters.append(page_limit + 1)

        rows = self.connection.execute(
            f"""
            SELECT revision_id,
                   revision_code,
                   manufacturing_records,
                   physical_instances,
                   activated_instances,
                   failed_instances,
                   removed_instances,
                   superseded_instances,
                   failure_records,
                   created_at
            FROM lifecycle_revision_outcomes_materialized
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at, revision_id
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

    @staticmethod
    def _failure_scope(
        *,
        part_id: Optional[str],
        revision_id: Optional[str],
    ) -> tuple[list[str], list[object]]:
        if revision_id is not None:
            clauses = ["scope_type = 'REVISION'", "scope_id = ?"]
            parameters: list[object] = [revision_id]
            if part_id is not None:
                clauses.append("part_id = ?")
                parameters.append(part_id)
            return clauses, parameters
        if part_id is not None:
            return ["scope_type = 'PART'", "scope_id = ?"], [part_id]
        return ["scope_type = 'GLOBAL'", "scope_id = '*'"] , []

    def failure_patterns(
        self,
        *,
        part_id: Optional[str] = None,
        revision_id: Optional[str] = None,
    ) -> tuple[FailurePatternSummary, ...]:
        clauses, parameters = self._failure_scope(
            part_id=part_id,
            revision_id=revision_id,
        )
        rows = self.connection.execute(
            f"""
            SELECT failure_type,
                   damage_location,
                   confirmed_cause,
                   occurrence_count,
                   revision_count,
                   instance_count,
                   first_failed_at,
                   last_failed_at
            FROM lifecycle_failure_patterns_materialized
            WHERE {' AND '.join(clauses)}
            ORDER BY occurrence_count DESC,
                     failure_type,
                     damage_location,
                     cause_null_rank,
                     cause_sort
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
        filters = {"part_id": part_id, "revision_id": revision_id}
        fingerprint, state = self._paging_state(
            query_name="failure_patterns_page",
            filters=filters,
            cursor=cursor,
        )
        if isinstance(state, KnowledgeCursorState):
            return super().failure_patterns_page(
                part_id=part_id,
                revision_id=revision_id,
                limit=page_limit,
                cursor=cursor,
            )

        clauses, parameters = self._failure_scope(
            part_id=part_id,
            revision_id=revision_id,
        )
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
            clauses.append(
                "(occurrence_count < ? "
                "OR (occurrence_count = ? AND failure_type > ?) "
                "OR (occurrence_count = ? AND failure_type = ? "
                "AND damage_location > ?) "
                "OR (occurrence_count = ? AND failure_type = ? "
                "AND damage_location = ? AND cause_null_rank > ?) "
                "OR (occurrence_count = ? AND failure_type = ? "
                "AND damage_location = ? AND cause_null_rank = ? "
                "AND cause_sort > ?))"
            )
            parameters.extend(
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
        parameters.append(page_limit + 1)

        rows = self.connection.execute(
            f"""
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
            FROM lifecycle_failure_patterns_materialized
            WHERE {' AND '.join(clauses)}
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
