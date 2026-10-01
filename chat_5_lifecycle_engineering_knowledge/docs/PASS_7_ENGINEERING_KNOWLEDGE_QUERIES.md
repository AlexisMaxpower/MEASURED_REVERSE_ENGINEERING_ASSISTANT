# Pass 7 — Deterministic Engineering Knowledge Queries

## Authorization and base

Pass 7 was started by direct user instruction after Pass 6 was frozen.

At branch start `main` still exposed Chat 5 directive `OD-2026-09-29-003`; no newer Chat-5-specific directive was present. To preserve the verified worker state, Pass 7 starts from frozen Pass 6 head:

```text
68791080a5440c6426ef28329302c99a323344b0
```

No shared contract, canonical fixture, CI workflow, integration test, schema migration, or other chat-owned file is modified.

## Goal

Turn the structured lifecycle facts from Passes 1-6 into a deterministic engineering knowledge query surface without adding AI interpretation.

The layer answers factual questions such as:

- what is the revision ancestry for this part?;
- how many manufactured/activated/failed/superseded instances exist per revision?;
- what physically occupied this equipment position over time?;
- which recorded failure patterns recur?;
- what instance replaced this failed/removed instance?

It does **not** claim that a revision is better or worse, infer root cause, recommend design changes, or synthesize unrecorded facts.

## Public read-only surface

`SQLiteLifecycleReadOnlySession` now exposes:

```python
session.knowledge
```

This is an instance of `SQLiteEngineeringKnowledgeRepository` and shares the same verified read-only SQLite connection as `session.queries`.

Therefore engineering knowledge queries inherit the Pass-6 guarantees:

```text
SQLite mode=ro
PRAGMA query_only = ON
snapshot_version == read_model_version
current relational schema required
```

No knowledge query can repair or mutate the database.

## Revision lineage

`revision_lineage(part_id)` returns ordered `RevisionLineageEntry` facts:

- revision identity;
- revision code;
- parent revision;
- creation timestamp;
- deterministic lineage depth.

The query fails closed with `LifecycleKnowledgeIntegrityError` when:

- a revision references a parent not present in the same part history;
- the parent graph contains a cycle.

It does not silently flatten invalid ancestry.

## Revision outcome summary

`revision_outcomes(part_id)` returns factual counters for each revision:

- manufacturing records;
- physical instances;
- activated instances;
- failed instances;
- removed instances;
- superseded instances;
- failure records.

Counts use distinct recorded identities so joins across events do not inflate them.

The result is deliberately named **outcome summary**, not effectiveness score. No ranking or quality conclusion is produced.

## Equipment / position history

`equipment_position_history(equipment_id, position=None)` returns the complete recorded physical event history for the requested equipment location:

- instance;
- part/revision/manufacturing identities;
- event type and time;
- sequence;
- replacement identity;
- recorded notes.

Ordering is deterministic by `(occurred_at, sequence, event_id)`.

Unlike current occupancy, this query preserves removed and superseded history.

## Recurring failure patterns

`failure_patterns(part_id=None, revision_id=None)` groups only exact recorded failure facts by:

```text
failure_type
+ damage_location
+ confirmed_cause
```

For every group it returns:

- occurrence count;
- distinct revision count;
- distinct physical instance count;
- first recorded failure time;
- last recorded failure time.

A null confirmed cause remains a separate factual group. The query never converts `estimated_cause` into `confirmed_cause` and never derives causal explanations.

## Replacement chain

`replacement_chain(instance_id)` follows explicit `SUPERSEDED.replacement_instance_id` links.

Every chain entry contains:

- instance identity;
- revision identity;
- manufacturing identity;
- latest physical state;
- next replacement identity, if recorded.

The traversal fails closed on:

- replacement cycles;
- missing replacement instance identity;
- instance with no valid physical state.

Unknown starting instance returns an empty tuple.

## Schema decision

Pass 7 adds **no SQLite migration**.

All required facts were already normalized by Pass 5:

- `lifecycle_revisions`;
- `lifecycle_manufacturing`;
- `lifecycle_physical_instances`;
- `lifecycle_failures`;
- `lifecycle_physical_events_relational`.

Adding duplicate derived tables would create an unnecessary second persistence concern. Knowledge remains a deterministic query/projection layer over committed facts.

## Deterministic acceptance dataset

`tests/test_engineering_knowledge.py` builds lifecycle state exclusively through the existing domain services and Unit of Work:

```text
R1 → R2 → R3
R1/M1/PI-1 → installed → tested → active → failed → removed
R2/M2/PI-2 → installed in same position → tested → active
PI-1 → superseded by PI-2
R1/M3/PI-3 → second equipment → active → same recorded failure pattern → removed
```

The tests verify:

1. lineage depths `R1=0`, `R2=1`, `R3=2`;
2. exact per-revision outcome counts;
3. equipment position history retains both old and replacement instances;
4. replacement chain is `PI-1 → PI-2`;
5. repeated `CRACK/HINGE_ROOT/FATIGUE` failures group to exactly two occurrences across two physical instances;
6. a revision with no matching failures returns no pattern;
7. corrupted cyclic lineage is rejected fail-closed.

## Independent verification

GitHub-hosted Chat 5 CI on implementation SHA `adca8d3dd60b2c727689c9969d4d0ba0d8178384`:

```text
35 passed in 1.32s
```

Final handoff is published only after the required Chat 5, canonical contract and Chat 4 → Chat 5 gates are green on the documented pre-handoff head.

## Intentionally still open

- semantic/AI interpretation of failure patterns;
- recommendations and design-change proposals;
- confidence/evidence scoring for inferred conclusions;
- REST/API boundary;
- richer filters and pagination for large histories;
- incremental/materialized analytical aggregates for large databases;
- field-device synchronization.
