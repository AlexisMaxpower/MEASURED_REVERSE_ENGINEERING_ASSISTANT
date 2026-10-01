# Build / Reuse Check — Pass 11 Failure-Pattern Aggregate Keyset Pagination

**Date:** 2026-10-01  
**Slice:** Chat 5 — Lifecycle & Engineering Knowledge  
**Branch:** `chat-5/pass-11`

## Problem

`failure_patterns_page()` was the last paginated engineering-knowledge query still using OFFSET for new traversals. Unlike revision outcomes and equipment history, it orders grouped results by a derived aggregate:

```text
COUNT(*) DESC
```

A safe migration therefore cannot reuse the row-history predicate verbatim.

## Reuse

Reuse existing components:

- `mrea.knowledge-cursor.v2`;
- query/filter fingerprinting;
- committed snapshot binding;
- legacy v1 cursor decoder;
- `KnowledgePage`;
- existing `FailurePatternSummary` factual projection;
- Pass-10 HMAC wrapper, which treats the inner cursor as opaque.

No external package is required.

## Build

Extend only `SQLiteKeysetEngineeringKnowledgeRepository.failure_patterns_page()`.

New traversal model:

```text
raw lifecycle_failures
→ grouped CTE
→ factual aggregates
→ total deterministic ordering
→ keyset predicate over grouped result
→ LIMIT + 1
→ v2 cursor
```

Key:

```text
(
  occurrence_count DESC,
  failure_type ASC,
  damage_location ASC,
  cause_null_rank ASC,
  cause_sort ASC
)
```

The final two fields distinguish `NULL` from an empty confirmed cause while preserving the existing normalized cause ordering.

## Backward compatibility

Already-issued `mrea.knowledge-cursor.v1` cursors remain on the exact historical OFFSET query/order. They are not silently reinterpreted as aggregate keysets.

New traversals emit v2.

## Truth boundary

This change modifies pagination execution only. It does not:

- infer a failure cause;
- rank revision quality;
- recommend a material or geometry;
- change failure grouping fields;
- mutate lifecycle facts;
- change shared canonical contracts.

## Lock-in risk

Low. SQL uses standard grouping plus SQLite-compatible CTE/predicate syntax and remains isolated behind the existing knowledge repository interface.

## Fallback

Legacy v1 traversal remains supported for cursors already in flight. If a future backend replaces SQLite, the same ordered aggregate key contract can be implemented in that adapter without changing the public factual DTO.
