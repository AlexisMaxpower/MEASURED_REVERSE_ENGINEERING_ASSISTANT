from __future__ import annotations

from datetime import datetime

from .engineering_knowledge import LifecycleKnowledgeIntegrityError
from .materialized_knowledge import SQLiteMaterializedEngineeringKnowledgeRepository
from .models import LifecycleState
from .projections import RevisionComparisonResult


_CANONICAL_STATE_BY_EVENT = {
    "REVISION_CREATED": LifecycleState.DRAFT,
    "MANUFACTURED": LifecycleState.MANUFACTURED,
    "INSTALLED": LifecycleState.ACTIVE,
    "TESTED": LifecycleState.ACTIVE,
    "FAILED": LifecycleState.FAILED,
}


class SQLiteRevisionComparisonEngineeringKnowledgeRepository(
    SQLiteMaterializedEngineeringKnowledgeRepository
):
    """Snapshot-bound durable revision comparison over committed lifecycle facts.

    This repository closes the gap between the original in-memory RevisionComparison
    projection and the durable read-only knowledge surface. It intentionally preserves
    the existing factual result shape and revision-level state semantics; no ranking,
    recommendation, causality inference or AI interpretation is introduced.
    """

    def compare_revisions(
        self,
        left_revision_id: str,
        right_revision_id: str,
    ) -> RevisionComparisonResult:
        left = self._revision_comparison_facts(left_revision_id)
        right = self._revision_comparison_facts(right_revision_id)

        if left is None or right is None:
            raise ValueError("both revisions must exist")
        if left[0] != right[0]:
            raise ValueError("cannot compare revisions from different parts")

        return RevisionComparisonResult(
            left_revision_id=left_revision_id,
            right_revision_id=right_revision_id,
            left_materials=left[1],
            right_materials=right[1],
            left_failure_count=left[2],
            right_failure_count=right[2],
            left_test_count=left[3],
            right_test_count=right[3],
            left_state=left[4],
            right_state=right[4],
        )

    def _revision_comparison_facts(
        self,
        revision_id: str,
    ) -> tuple[str, tuple[str, ...], int, int, LifecycleState] | None:
        identity = self.connection.execute(
            """
            SELECT r.part_id,
                   (SELECT COUNT(*)
                      FROM lifecycle_failures AS f
                     WHERE f.revision_id = r.revision_id) AS failure_count,
                   (SELECT COUNT(*)
                      FROM lifecycle_tests AS t
                     WHERE t.revision_id = r.revision_id) AS test_count
            FROM lifecycle_revisions AS r
            WHERE r.revision_id = ?
            """,
            (revision_id,),
        ).fetchone()
        if identity is None:
            return None

        material_rows = self.connection.execute(
            """
            SELECT DISTINCT material
            FROM lifecycle_manufacturing
            WHERE revision_id = ?
            ORDER BY material
            """,
            (revision_id,),
        ).fetchall()
        materials = tuple(str(row[0]) for row in material_rows)

        event_rows = self.connection.execute(
            """
            SELECT event_type, occurred_at, sequence
            FROM lifecycle_events_relational
            WHERE revision_id = ?
            """,
            (revision_id,),
        ).fetchall()
        state = self._revision_state(revision_id, event_rows)

        return (
            str(identity[0]),
            materials,
            int(identity[1]),
            int(identity[2]),
            state,
        )

    @staticmethod
    def _revision_state(
        revision_id: str,
        rows: list[object],
    ) -> LifecycleState:
        if not rows:
            raise LifecycleKnowledgeIntegrityError(
                f"revision has no lifecycle events: {revision_id}"
            )

        events: list[tuple[str, datetime, int]] = []
        for row in rows:
            try:
                event_type = str(row[0])  # type: ignore[index]
                occurred_at = datetime.fromisoformat(str(row[1]))  # type: ignore[index]
                sequence = int(row[2])  # type: ignore[index]
            except (IndexError, TypeError, ValueError) as exc:
                raise LifecycleKnowledgeIntegrityError(
                    f"invalid lifecycle event row for revision: {revision_id}"
                ) from exc
            events.append((event_type, occurred_at, sequence))

        latest_failure = max(
            (event for event in events if event[0] == "FAILED"),
            key=lambda event: (event[1], event[2]),
            default=None,
        )
        if latest_failure is not None:
            latest_install = max(
                (event for event in events if event[0] == "INSTALLED"),
                key=lambda event: (event[1], event[2]),
                default=None,
            )
            if latest_install is None or (latest_failure[1], latest_failure[2]) > (
                latest_install[1],
                latest_install[2],
            ):
                return LifecycleState.FAILED

        latest = max(events, key=lambda event: (event[1], event[2]))
        try:
            return _CANONICAL_STATE_BY_EVENT[latest[0]]
        except KeyError as exc:
            raise LifecycleKnowledgeIntegrityError(
                f"cannot project state from event type: {latest[0]}"
            ) from exc
