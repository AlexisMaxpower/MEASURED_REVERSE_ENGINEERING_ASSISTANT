# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-30**
- Branch: `chat-5/pass-7`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Pass 7 authorization: **direct user instruction; no newer Chat-5-specific directive present on `main` at branch start**
- Base SHA: `68791080a5440c6426ef28329302c99a323344b0` (frozen Chat 5 Pass 6)
- State: **deterministic engineering knowledge query layer implemented; required pre-handoff gates green; handoff published and branch ready for final freeze commit**

## Preserved baseline

Still active and unchanged:

- Revision / Manufacturing / Installation / Test / Failure domain;
- canonical CADPackage + CADVerificationReport transfer;
- VERIFIED manufacturing eligibility gate;
- canonical `LifecycleEvent v1` adapter;
- physical-instance state machine;
- exact instance/evidence linkage;
- equipment/position occupancy protection;
- removal/replacement/supersession semantics;
- LifecycleRepository + LifecycleUnitOfWork;
- authoritative SQLite snapshot;
- normalized relational read model and migrations;
- SQL-native lifecycle queries;
- verified backup/restore;
- read-only SQLite query session.

No shared contract, canonical fixture, CI workflow, integration test, SQLite migration, or other chat-owned file was changed.

## Pass 7 additions

### SQLiteEngineeringKnowledgeRepository

Added a deterministic factual knowledge-query layer over the existing normalized relational facts.

Public read-only access:

```python
with SQLiteLifecycleReadOnlySession("lifecycle.db") as session:
    session.knowledge.revision_lineage("PART-0042")
```

The same read-only connection is reused, preserving:

```text
mode=ro
query_only=ON
snapshot_version == read_model_version
```

### Revision lineage

`revision_lineage(part_id)` returns:

- revision_id;
- revision_code;
- parent_revision_id;
- created_at;
- deterministic lineage depth.

It rejects missing-parent and cyclic ancestry with `LifecycleKnowledgeIntegrityError`.

### Revision outcomes

`revision_outcomes(part_id)` returns distinct factual counts per revision:

- manufacturing records;
- physical instances;
- activated instances;
- failed instances;
- removed instances;
- superseded instances;
- failure records.

No effectiveness score or better/worse ranking is generated.

### Equipment history

`equipment_position_history(equipment_id, position=None)` returns all recorded physical lifecycle events at the requested equipment location, including removed and superseded history.

Ordering is deterministic by timestamp, sequence and event ID.

### Failure patterns

`failure_patterns(part_id=None, revision_id=None)` groups only exact stored facts by:

```text
failure_type + damage_location + confirmed_cause
```

It reports occurrence count, distinct revision/instance counts and first/last failure timestamps.

Estimated cause is never promoted to confirmed cause.

### Replacement chains

`replacement_chain(instance_id)` follows explicit `SUPERSEDED.replacement_instance_id` relationships and returns exact instance/revision/manufacturing identity plus latest state.

It rejects cycles, missing replacement instances and invalid state histories.

## Schema decision

No schema migration was added.

Pass 5 already persists all facts needed by Pass 7. The knowledge layer therefore remains a query/projection surface instead of introducing duplicate derived tables.

## Verification

### Acceptance dataset

`tests/test_engineering_knowledge.py` creates facts only through existing domain services and Unit of Work:

```text
R1 -> R2 -> R3
PI-1 (R1) -> active -> failed -> removed
PI-2 (R2) -> same equipment/position -> active
PI-1 -> superseded by PI-2
PI-3 (R1) -> second equipment -> same recorded failure pattern -> removed
```

Coverage includes:

1. deterministic revision lineage/depth;
2. distinct per-revision factual outcome counts;
3. full equipment-position history;
4. explicit replacement chain;
5. exact repeated failure grouping across physical instances;
6. empty no-match failure pattern;
7. cyclic lineage fail-closed behavior.

### GitHub-hosted Chat 5 suite

Implementation SHA:

```text
adca8d3dd60b2c727689c9969d4d0ba0d8178384
```

Exact result:

```text
35 passed in 1.32s
```

Status: **SUCCESS**.

### Pre-handoff required gates

SHA:

```text
f61ec8a880624f40e1b4e6c7b5042fd9135f7195
```

Workflow run:

```text
36645177818
```

Results:

- `Chat 5 / Lifecycle` — **SUCCESS**;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**.

## Files added in Pass 7

- `src/mrea_lifecycle/engineering_knowledge.py`;
- `tests/test_engineering_knowledge.py`;
- `docs/PASS_7_ENGINEERING_KNOWLEDGE_QUERIES.md`.

## Files modified in Pass 7

- `src/mrea_lifecycle/read_only.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Known limitations

Still open:

- AI/semantic interpretation of factual patterns;
- design-change recommendations;
- evidence/confidence scoring for inferred conclusions;
- REST/API;
- pagination/materialized aggregates for large histories;
- field-device synchronization.

## Handoff rule

`ORCHESTRATOR_HANDOFF.md` is the final worker commit after this state reconciliation. `chat-5/pass-7` is frozen after that commit. No later commit is allowed unless final verification finds a real missing/incorrect GitHub file or Chat 6 explicitly requests a correction.
