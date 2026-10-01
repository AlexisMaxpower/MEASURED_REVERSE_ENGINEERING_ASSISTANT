# Pass 11 — Aggregate Keyset Pagination for Failure Patterns

**Date:** 2026-10-01  
**Branch:** `chat-5/pass-11`  
**Authorization:** direct user instruction  
**Central coordination baseline:** current `main` plus file-level replay of Chat-5 cumulative Pass 9–10.1 state and the corrected Round-4 runtime-truth delta.

## Goal

Remove OFFSET from new grouped `failure_patterns_page()` traversals without weakening snapshot/query binding or changing factual engineering semantics.

## Why this needed a separate pass

Failure-pattern ordering starts with a derived aggregate:

```text
COUNT(*) DESC
```

The Pass-10.1 row-history continuation predicates cannot be copied directly because the continuation boundary exists after `GROUP BY`.

## Implementation

`SQLiteKeysetEngineeringKnowledgeRepository.failure_patterns_page()` now has two explicit execution modes.

### New traversal

```text
cursor = None / mrea.knowledge-cursor.v2
→ grouped CTE
→ aggregate-aware key predicate
→ LIMIT + 1
→ mrea.knowledge-cursor.v2
```

Continuation order:

```text
occurrence_count DESC
failure_type ASC
damage_location ASC
cause_null_rank ASC
cause_sort ASC
```

Cursor key:

```text
(occurrence_count, failure_type, damage_location, cause_null_rank, cause_sort)
```

`cause_null_rank` is `0` for `NULL`, `1` otherwise. `cause_sort` is `COALESCE(confirmed_cause, '')`. Together they make the grouped order total even when `NULL` and empty-string causes normalize to the same text.

### Existing v1 traversal

A valid `mrea.knowledge-cursor.v1` continues through the original OFFSET query and original ordering.

This is deliberate compatibility behavior: an in-flight traversal is completed under the semantics that issued its cursor rather than being silently switched mid-stream.

## Fail-closed cursor validation

A v2 failure-pattern cursor must contain exactly five typed values:

1. non-boolean integer occurrence count;
2. failure type string;
3. damage-location string;
4. integer null rank (`0` or `1`);
5. normalized cause string.

Malformed keysets raise `LifecycleKnowledgeCursorError` before query execution.

## Preserved truth

Unchanged:

- factual grouping by `failure_type`, `damage_location`, `confirmed_cause`;
- occurrence/revision/instance counts;
- first/last failure timestamps;
- query/filter fingerprint;
- committed snapshot binding;
- HMAC HTTP cursor wrapping;
- lifecycle/CAD/manufacturing semantics;
- shared contracts and fixtures.

No AI interpretation or recommendation is introduced.

## Tests

`tests/test_failure_pattern_keyset_pagination.py` covers:

- v2 cursor emission for grouped results;
- complete traversal without duplicates/gaps;
- aggregate-count descending continuation;
- deterministic tie-breaking including `NULL` versus empty cause;
- v2 continuation SQL contains key predicates and no OFFSET;
- legacy v1 cursor remains on OFFSET path;
- malformed aggregate keyset fails closed.
