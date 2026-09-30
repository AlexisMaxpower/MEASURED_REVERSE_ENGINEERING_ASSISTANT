# Pass 8 — Snapshot-Bound Engineering Knowledge Pagination

## Authorization and base

Pass 8 was started by direct user instruction after Pass 7 was frozen.

At branch start, repository `main` still exposed Chat 5 directive `OD-2026-09-29-003`; no newer Chat-5-specific directive was available. To preserve the verified worker state, Pass 8 starts from frozen Pass 7 head:

```text
d9bed012eb8bbcea338522847a46572bb5415026
```

No shared contract, canonical fixture, CI workflow, integration test, SQLite migration, or other chat-owned file is modified.

## Goal

Make deterministic engineering knowledge queries safe to consume in bounded pages without sacrificing the read-only and snapshot-consistency guarantees established in Passes 5-7.

The key invariant is:

```text
cursor
→ exact query/filter fingerprint
→ exact committed snapshot_version
→ deterministic offset
```

A cursor cannot be silently reused for a different query/filter set or after the lifecycle database advances to a newer committed snapshot.

## Cursor format

Cursor format:

```text
mrea.knowledge-cursor.v1
```

The cursor is URL-safe base64 text containing an opaque envelope with:

- format version;
- SHA-256 query fingerprint;
- committed lifecycle snapshot version;
- deterministic offset;
- SHA-256 checksum of the cursor payload.

The checksum is an integrity/corruption check, not an authentication mechanism. The cursor contains no authorization decision or secret data.

## Query fingerprint

The fingerprint is SHA-256 over canonical JSON containing:

```text
query name + normalized filter set
```

For example, an equipment-history cursor issued for:

```text
equipment_id = EQ-01
position = LEFT
event_type = null
revision_id = null
instance_id = null
```

cannot be reused after changing `event_type`, equipment, position, revision, or instance filter.

Changing the page size is allowed because page size is not part of query identity; the next offset remains deterministic.

## Snapshot binding

`SQLiteLifecycleReadOnlySession` now constructs `SQLiteEngineeringKnowledgeRepository` with the exact verified `snapshot_version` observed when the read-only session opens.

A cursor carries that version. On continuation:

```text
cursor.snapshot_version == session.snapshot_version
```

is mandatory.

If a writer commits a newer lifecycle snapshot and a new reader attempts to continue an old cursor, `LifecycleKnowledgeCursorError` is raised instead of silently mixing two database versions.

## Public pagination types

Added:

- `KnowledgePage[T]`;
- `LifecycleKnowledgeCursorError`;
- `KNOWLEDGE_CURSOR_FORMAT_VERSION`;
- `DEFAULT_KNOWLEDGE_PAGE_LIMIT = 100`;
- `MAX_KNOWLEDGE_PAGE_LIMIT = 500`.

A page contains:

```text
items
next_cursor | null
snapshot_version
```

Limits must be integers from 1 through 500. Booleans and out-of-range values fail closed.

## Paginated knowledge queries

### Revision outcomes

```python
page = session.knowledge.revision_outcomes_page(
    "PART-0042",
    limit=100,
    cursor=None,
)
```

Ordering remains:

```text
revision.created_at, revision_id
```

### Equipment / position history

```python
page = session.knowledge.equipment_position_history_page(
    equipment_id="EQ-01",
    position="LEFT",
    event_type=None,
    revision_id=None,
    instance_id=None,
    limit=100,
    cursor=None,
)
```

Optional exact filters are available for:

- position;
- event type;
- revision ID;
- physical instance ID.

Ordering remains:

```text
occurred_at, sequence, event_id
```

### Failure patterns

```python
page = session.knowledge.failure_patterns_page(
    part_id="PART-0042",
    revision_id=None,
    limit=100,
    cursor=None,
)
```

Ordering remains the factual Pass-7 ordering:

```text
occurrence_count DESC,
failure_type,
damage_location,
confirmed_cause
```

## Queries deliberately not cursor-paged in this pass

### Revision lineage

`revision_lineage()` remains a whole-graph integrity query because deterministic lineage depth requires validating the complete parent graph for missing parents and cycles.

### Replacement chain

`replacement_chain()` remains a whole-chain integrity traversal because every link must be checked for cycles, missing replacement identities and valid physical state.

Artificially page-splitting either graph operation would weaken the existing fail-closed integrity guarantee.

## Backward compatibility

All Pass-7 tuple-returning knowledge methods remain unchanged:

- `revision_lineage()`;
- `revision_outcomes()`;
- `equipment_position_history()`;
- `failure_patterns()`;
- `replacement_chain()`.

Pagination is additive.

No SQLite schema migration was required because Pass 8 only changes query execution and cursor state.

## Deterministic verification

`tests/test_engineering_knowledge_paging.py` verifies:

1. five revision outcome rows traverse page sizes of two with no duplicate or missing revision;
2. every page reports the read-only session snapshot version;
3. equipment history continues deterministically across pages;
4. a cursor is rejected when a filter set changes;
5. an old cursor is rejected after a writer advances the database to the next committed snapshot;
6. a modified cursor is rejected;
7. limits `0` and `501` are rejected;
8. two distinct failure-pattern groups traverse page size one with no loss;
9. paginated failure-pattern results exactly equal the existing non-paginated factual query;
10. legacy revision outcome query ordering remains unchanged.

Independent GitHub-hosted Chat 5 CI on implementation SHA `1a6803bff00eeaa43ffb18fb18c86695c59403d2`:

```text
40 passed in 1.51s
```

## Build / Reuse decision

Reused:

- existing normalized Pass-5 SQLite read model;
- Pass-6 verified read-only session;
- Pass-7 factual engineering knowledge semantics;
- Python stdlib `base64`, `hashlib`, `json`.

Not introduced:

- schema migration;
- materialized aggregate tables;
- REST framework;
- external cursor/session store;
- AI interpretation;
- shared contract amendment.

## Intentionally still open

- REST/API transport around the read-only query surface;
- authenticated/externally-issued cursor signing if cursors cross a trust boundary;
- keyset pagination if very large datasets make offset pagination insufficient;
- materialized analytical aggregates for very large histories;
- semantic/AI interpretation;
- field-device synchronization.
