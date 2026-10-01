# Chat 2 — Pass 15 Implementation Report

## Baseline

Pass 15 starts from certified shared `main`:

`99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

Directive: `OD-2026-10-01-008`.

## Goal

Close the Pass-14 large-local-set debt by adding bounded deterministic keyset traversal for durable `MeasurementSession` storage without changing canonical/shared contracts or the existing private payload schema.

## Query contract

Added:

```python
MeasurementSessionPageCursor
MeasurementSessionPage
list_session_page(
    *,
    project_id: str | None = None,
    limit: int = 50,
    cursor: MeasurementSessionPageCursor | None = None,
) -> MeasurementSessionPage
```

The same semantics are exposed by:

- `InMemoryMeasurementSessionRepository`;
- `SqliteMeasurementSessionRepository`;
- `MeasurementSessionService`.

Ordering remains the Pass-14 order:

```text
created_at DESC, session_id ASC
```

The cursor is bound to the optional normalized `project_id` scope. Reusing a cursor under a different project scope fails closed.

## SQLite keyset implementation

Pass 15 adds private query metadata to `measurement_sessions`:

- `project_id TEXT`;
- `created_at_utc_us INTEGER`.

Indexes:

- `idx_measurement_sessions_order(created_at_utc_us DESC, session_id ASC)`;
- `idx_measurement_sessions_project_order(project_id, created_at_utc_us DESC, session_id ASC)`.

A page request uses a keyset predicate instead of `OFFSET`:

```text
created_at_utc_us < cursor.created_at
OR
(created_at_utc_us = cursor.created_at AND session_id > cursor.session_id)
```

Only `limit + 1` candidate rows are loaded/decoded to determine whether another page exists.

`created_at` is normalized to exact integer UTC microseconds without float timestamps, so ordering remains correct across timezone offsets.

## Backward compatibility / migration

The payload schema remains exactly:

`mrea.chat2.measurement-session.local.v1`

Existing Pass-13/14 databases that lack query metadata are migrated transactionally at repository initialization:

1. missing private columns are added;
2. rows with missing metadata are decoded through the existing validated payload decoder;
3. `project_id` and UTC-microsecond timestamp are backfilled;
4. keyset indexes are created.

Corrupt/unsupported legacy rows fail closed during backfill; they are not silently indexed or omitted.

No canonical contract or fixture changes are required.

## Truth protection

Every paged SQLite row is decoded through the existing payload validation and then checked against indexed query metadata. Metadata/payload mismatch fails closed.

Measurement provenance, explicit confirmation, uncertainty, raw anchors and verified truth semantics are unchanged.

## Compatibility

Existing `list_sessions(project_id=...)` remains available. The SQLite implementation now traverses the durable store in bounded internal pages rather than decoding the entire table in one query.

Page-size validation is bounded to `1..500` and rejects booleans/non-integers.

## Tests

Added `tests/test_pass15_session_pagination.py` covering:

1. multi-page SQLite traversal after reopen with no duplicate or missing sessions;
2. project-scoped pagination and cursor scope binding;
3. stable equal-timestamp `session_id` tie-break across in-memory and SQLite backends;
4. absolute-instant ordering across timezone offsets;
5. page limit and cursor datetime validation;
6. migration/backfill of a Pass-14 table with no query metadata columns;
7. fail-closed migration of a corrupt legacy row;
8. fail-closed indexed-metadata drift detection;
9. service-level paged query exposure.

## Ownership / boundaries

Only `chat_2_physical_measurement/` is changed.

No shared contract, canonical fixture, Chat-1/3/4/5 source, shared CI, geometry normalization, CAD or lifecycle logic is modified.

## Remaining persistence debt

- no multi-process writer/read stress benchmark;
- no explicit external migration CLI/maintenance command;
- runtime composition still must choose the durable repository where persistence is required.
