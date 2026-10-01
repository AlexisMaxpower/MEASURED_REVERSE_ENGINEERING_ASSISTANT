# Pass 10.1 — Keyset Pagination for Large Engineering Histories

## Authorization and orchestration status

Pass 10.1 was started by direct user instruction after Pass 10 was frozen.

At branch start, `main` contained Chat 6 directive `OD-2026-09-30-004`, which selected frozen Chat 5 Pass 8 for central Round-4 review and requested no new normal worker implementation. Pass 10.1 is therefore explicitly a **user-authorized out-of-band worker continuation** and is not represented as accepted central Round-4 work.

Branch base:

```text
8044451abd050f69556c9274aec1a83caefad408
```

No selected Pass-8 branch, shared contract, CI workflow, integration test, or other chat-owned file is modified.

## Goal

Replace OFFSET-based continuation for the highest-cardinality engineering-history queries with deterministic keyset continuation while preserving:

- query/filter binding;
- committed snapshot binding;
- existing HMAC HTTP cursor wrapper;
- backward continuation of already-issued Pass-8/9/10 v1 offset cursors.

## Cursor versions

Legacy cursor remains:

```text
mrea.knowledge-cursor.v1
```

New keyset cursor:

```text
mrea.knowledge-cursor.v2
```

V2 payload contains:

```text
v  format version
q  query/filter fingerprint
s  committed snapshot version
k  ordered keyset tuple
```

The existing checksum envelope remains in place. If the HTTP HMAC wrapper from Pass 10 is enabled, the entire inner v2 cursor is authenticated without interpretation by the HTTP layer.

## Backward compatibility

`decode_knowledge_keyset_cursor()` accepts both:

- v2 keyset cursor;
- v1 offset cursor.

If a traversal started before Pass 10.1 with a valid v1 cursor, the traversal may finish using the legacy OFFSET path for that cursor chain. New traversals emit v2 cursors for the migrated high-cardinality queries.

Query fingerprint and snapshot version remain mandatory for both versions.

## Keyset queries

### Revision outcomes

Ordering:

```text
revision.created_at ASC,
revision_id ASC
```

V2 continuation key:

```text
(created_at, revision_id)
```

Continuation predicate:

```text
created_at > last_created_at
OR (created_at = last_created_at AND revision_id > last_revision_id)
```

The v2 SQL path uses `LIMIT` only and does not use `OFFSET`.

### Equipment / position history

Ordering:

```text
occurred_at ASC,
sequence ASC,
event_id ASC
```

V2 continuation key:

```text
(occurred_at, sequence, event_id)
```

Continuation predicate advances lexicographically over the same ordered tuple.

The event sequence and event ID provide deterministic tie-breaking even when event timestamps are equal.

## Queries deliberately unchanged

`failure_patterns_page()` remains snapshot-bound OFFSET pagination in Pass 10.1.

Reason: it is an aggregate/grouped query whose ordering starts with a derived `COUNT(*) DESC`. Moving it to keyset safely requires a dedicated aggregate-keyset design and is not necessary to remove OFFSET from the large row-oriented history traversals addressed by this pass.

Whole-graph/whole-chain operations remain unchanged:

- `revision_lineage()`;
- `replacement_chain()`.

## Runtime integration

Added `SQLiteKeysetEngineeringKnowledgeRepository`, a subclass of the existing factual knowledge repository.

`SQLiteLifecycleReadOnlySession` now instantiates this adapter while keeping its public `.knowledge` contract compatible with `SQLiteEngineeringKnowledgeRepository`.

No factual grouping, lifecycle interpretation, or domain semantics are duplicated.

## Verification

Added `tests/test_keyset_pagination_v2.py`.

Coverage verifies:

1. revision outcomes emit a v2 keyset cursor;
2. six revisions traverse without duplicate or missing rows;
3. continuation SQL for a v2 revision cursor contains key predicates and no `OFFSET`;
4. a valid legacy v1 offset cursor is still accepted;
5. equipment history uses a three-part `(occurred_at, sequence, event_id)` keyset;
6. existing Pass-9/10 HTTP and HMAC tests continue to execute against the new inner cursor format.

Independent GitHub-hosted implementation run on SHA `e1265ad57bf602b0acd44ed029ed1b6e6ccd6666`:

```text
57 passed in 1.96s
```

## Build / reuse decision

Reused:

- Pass-7 factual knowledge repository;
- Pass-8 query fingerprint and snapshot binding;
- Pass-9 HTTP transport;
- Pass-10 HMAC cursor authentication;
- current normalized SQLite read model.

Not introduced:

- schema migration;
- materialized table;
- external cursor store;
- framework dependency;
- shared contract change;
- AI inference.

## Known limitations

Still open:

- aggregate keyset pagination for `failure_patterns_page()`;
- materialized analytical aggregates;
- API client authentication/authorization;
- deployment/TLS/rate-limit policy;
- semantic/AI interpretation;
- field-device synchronization.
