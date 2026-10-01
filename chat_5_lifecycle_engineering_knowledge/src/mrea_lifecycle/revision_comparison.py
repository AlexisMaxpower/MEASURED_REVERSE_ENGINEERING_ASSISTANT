from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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


@dataclass(frozen=True, slots=True)
class RevisionManufacturingFact:
    manufacturing_id: str
    material: str
    method: str
    manufactured_at: datetime
    batch: Optional[str]
    machine: Optional[str]
    print_profile: Optional[str]
    contractor: Optional[str]
    cost: Optional[str]
    post_processing: Optional[str]


@dataclass(frozen=True, slots=True)
class RevisionTestFact:
    test_id: str
    tested_at: datetime
    test_type: str
    conditions: str
    result: str
    conclusion: str
    manufacturing_id: Optional[str]
    installation_id: Optional[str]
    instance_id: Optional[str]
    artifact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RevisionFailureFact:
    failure_id: str
    failed_at: datetime
    failure_type: str
    damage_location: str
    circumstances: str
    manufacturing_id: Optional[str]
    installation_id: Optional[str]
    instance_id: Optional[str]
    estimated_cause: Optional[str]
    confirmed_cause: Optional[str]
    related_feature: Optional[str]
    evidence_artifact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RevisionComparisonSnapshot:
    revision_id: str
    part_id: str
    revision_code: str
    created_at: datetime
    parent_revision_id: Optional[str]
    origin: str
    notes: Optional[str]
    source_cad_artifact_id: Optional[str]
    verification_status: Optional[str]
    runtime_status: Optional[str]
    runtime_evidence_schema_version: Optional[str]
    runtime_real_host_executed: Optional[bool]
    state: LifecycleState
    manufacturing: tuple[RevisionManufacturingFact, ...]
    tests: tuple[RevisionTestFact, ...]
    failures: tuple[RevisionFailureFact, ...]

    @property
    def materials(self) -> tuple[str, ...]:
        return tuple(sorted({fact.material for fact in self.manufacturing}))

    @property
    def manufacturing_methods(self) -> tuple[str, ...]:
        return tuple(sorted({fact.method for fact in self.manufacturing}))


@dataclass(frozen=True, slots=True)
class RevisionComparisonDetailsResult:
    left: RevisionComparisonSnapshot
    right: RevisionComparisonSnapshot
    changed_categories: tuple[str, ...]


class SQLiteRevisionComparisonEngineeringKnowledgeRepository(
    SQLiteMaterializedEngineeringKnowledgeRepository
):
    """Snapshot-bound durable revision comparison over committed lifecycle facts.

    The compact comparison preserves the original in-memory result contract. The
    detailed comparison is additive and exposes only exact persisted facts already
    owned by Chat 5: revision metadata/provenance, manufacturing records, tests,
    failures/evidence and projected lifecycle state. It does not infer geometry,
    rank revisions, recommend a preferred revision, or claim causality.
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

    def compare_revision_details(
        self,
        left_revision_id: str,
        right_revision_id: str,
    ) -> RevisionComparisonDetailsResult:
        left = self._revision_detail_snapshot(left_revision_id)
        right = self._revision_detail_snapshot(right_revision_id)

        if left is None or right is None:
            raise ValueError("both revisions must exist")
        if left.part_id != right.part_id:
            raise ValueError("cannot compare revisions from different parts")

        changed_categories: list[str] = []
        if (
            left.parent_revision_id,
            left.origin,
            left.notes,
            left.source_cad_artifact_id,
        ) != (
            right.parent_revision_id,
            right.origin,
            right.notes,
            right.source_cad_artifact_id,
        ):
            changed_categories.append("revision_metadata")
        if (
            left.verification_status,
            left.runtime_status,
            left.runtime_evidence_schema_version,
            left.runtime_real_host_executed,
        ) != (
            right.verification_status,
            right.runtime_status,
            right.runtime_evidence_schema_version,
            right.runtime_real_host_executed,
        ):
            changed_categories.append("cad_truth")
        if left.materials != right.materials:
            changed_categories.append("materials")
        if left.manufacturing_methods != right.manufacturing_methods:
            changed_categories.append("manufacturing_methods")
        if left.manufacturing != right.manufacturing:
            changed_categories.append("manufacturing_records")
        if left.tests != right.tests:
            changed_categories.append("tests")
        if left.failures != right.failures:
            changed_categories.append("failures")
        if left.state is not right.state:
            changed_categories.append("lifecycle_state")

        return RevisionComparisonDetailsResult(
            left=left,
            right=right,
            changed_categories=tuple(changed_categories),
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

    def _revision_detail_snapshot(
        self,
        revision_id: str,
    ) -> RevisionComparisonSnapshot | None:
        revision_row = self.connection.execute(
            """
            SELECT revision_id, part_id, revision_code, created_at,
                   parent_revision_id, origin, notes, source_cad_artifact_id,
                   verification_status, runtime_status,
                   runtime_evidence_schema_version, runtime_real_host_executed
            FROM lifecycle_revisions
            WHERE revision_id = ?
            """,
            (revision_id,),
        ).fetchone()
        if revision_row is None:
            return None

        manufacturing_rows = self.connection.execute(
            """
            SELECT manufacturing_id, material, method, manufactured_at,
                   batch, machine, print_profile, contractor, cost,
                   post_processing
            FROM lifecycle_manufacturing
            WHERE revision_id = ?
            ORDER BY manufactured_at, manufacturing_id
            """,
            (revision_id,),
        ).fetchall()
        manufacturing = tuple(
            RevisionManufacturingFact(
                manufacturing_id=str(row[0]),
                material=str(row[1]),
                method=str(row[2]),
                manufactured_at=datetime.fromisoformat(str(row[3])),
                batch=row[4],
                machine=row[5],
                print_profile=row[6],
                contractor=row[7],
                cost=row[8],
                post_processing=row[9],
            )
            for row in manufacturing_rows
        )

        test_rows = self.connection.execute(
            """
            SELECT test_id, tested_at, test_type, conditions, result,
                   conclusion, manufacturing_id, installation_id, instance_id
            FROM lifecycle_tests
            WHERE revision_id = ?
            ORDER BY tested_at, test_id
            """,
            (revision_id,),
        ).fetchall()
        tests: list[RevisionTestFact] = []
        for row in test_rows:
            artifact_rows = self.connection.execute(
                """
                SELECT artifact_id
                FROM lifecycle_test_artifacts
                WHERE test_id = ?
                ORDER BY ordinal
                """,
                (row[0],),
            ).fetchall()
            tests.append(
                RevisionTestFact(
                    test_id=str(row[0]),
                    tested_at=datetime.fromisoformat(str(row[1])),
                    test_type=str(row[2]),
                    conditions=str(row[3]),
                    result=str(row[4]),
                    conclusion=str(row[5]),
                    manufacturing_id=row[6],
                    installation_id=row[7],
                    instance_id=row[8],
                    artifact_ids=tuple(str(item[0]) for item in artifact_rows),
                )
            )

        failure_rows = self.connection.execute(
            """
            SELECT failure_id, failed_at, failure_type, damage_location,
                   circumstances, manufacturing_id, installation_id,
                   instance_id, estimated_cause, confirmed_cause,
                   related_feature
            FROM lifecycle_failures
            WHERE revision_id = ?
            ORDER BY failed_at, failure_id
            """,
            (revision_id,),
        ).fetchall()
        failures: list[RevisionFailureFact] = []
        for row in failure_rows:
            evidence_rows = self.connection.execute(
                """
                SELECT artifact_id
                FROM lifecycle_failure_evidence
                WHERE failure_id = ?
                ORDER BY ordinal
                """,
                (row[0],),
            ).fetchall()
            failures.append(
                RevisionFailureFact(
                    failure_id=str(row[0]),
                    failed_at=datetime.fromisoformat(str(row[1])),
                    failure_type=str(row[2]),
                    damage_location=str(row[3]),
                    circumstances=str(row[4]),
                    manufacturing_id=row[5],
                    installation_id=row[6],
                    instance_id=row[7],
                    estimated_cause=row[8],
                    confirmed_cause=row[9],
                    related_feature=row[10],
                    evidence_artifact_ids=tuple(
                        str(item[0]) for item in evidence_rows
                    ),
                )
            )

        event_rows = self.connection.execute(
            """
            SELECT event_type, occurred_at, sequence
            FROM lifecycle_events_relational
            WHERE revision_id = ?
            """,
            (revision_id,),
        ).fetchall()

        raw_real_host_executed = revision_row[11]
        return RevisionComparisonSnapshot(
            revision_id=str(revision_row[0]),
            part_id=str(revision_row[1]),
            revision_code=str(revision_row[2]),
            created_at=datetime.fromisoformat(str(revision_row[3])),
            parent_revision_id=revision_row[4],
            origin=str(revision_row[5]),
            notes=revision_row[6],
            source_cad_artifact_id=revision_row[7],
            verification_status=revision_row[8],
            runtime_status=revision_row[9],
            runtime_evidence_schema_version=revision_row[10],
            runtime_real_host_executed=(
                bool(raw_real_host_executed)
                if raw_real_host_executed is not None
                else None
            ),
            state=self._revision_state(revision_id, event_rows),
            manufacturing=manufacturing,
            tests=tuple(tests),
            failures=tuple(failures),
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
