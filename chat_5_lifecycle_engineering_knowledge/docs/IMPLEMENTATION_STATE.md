# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-01**
- Branch: `chat-5/pass-11`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 11**
- Central repository baseline checked before work: `main` @ `c034f7583d4e1f130f827d94a43762f3cad1a7e5`
- Central directive observed: `OD-2026-09-30-004`
- State: **implementation prepared; CI/final handoff pending**

## Baseline reconciliation

Pass 10.1 and corrected Round-4 Pass 8 had diverged from common Chat-5 Pass-8 ancestry.

Pass 11 does not extend either stale tree blindly. It was rebuilt as:

```text
current main
→ file-level replay of Chat-5-owned cumulative Pass 9–10.1 surface
→ corrected Round-4 runtime-truth files from frozen chat-5/pass-8
→ Pass-11 aggregate keyset delta
```

Preserved from current `main`:

- Chat-6-owned `ORCHESTRATOR_DIRECTIVE.md`;
- Chat-6 `FIX_REQUIRED` control document;
- shared contracts/fixtures;
- root integration tests;
- workflows;
- all Chat 1–4 and Chat 6/7/8 surfaces.

The frozen `chat-5/pass-8` ref was not mutated.

## Preserved lifecycle truth

The cumulative line now includes the corrected Round-4 runtime boundary:

- `CADRuntimeStatus = VERIFIED | FAILED | UNVERIFIED`;
- runtime evidence persists through snapshot and normalized read model;
- runtime VERIFIED requires real-host execution evidence;
- runtime FAILED/UNVERIFIED blocks manufacturing when runtime evidence is supplied;
- canonical numerical verification remains separate;
- generic flows without a runtime gate remain backward compatible.

## Pass 11 addition

`failure_patterns_page()` now joins the Pass-10.1 keyset adapter.

New v2 aggregate key:

```text
(
  occurrence_count,
  failure_type,
  damage_location,
  cause_null_rank,
  cause_sort
)
```

Sort direction is:

```text
occurrence_count DESC
failure_type ASC
damage_location ASC
cause_null_rank ASC
cause_sort ASC
```

The grouped result is produced in a CTE; v2 continuation applies key predicates to the grouped rows and uses `LIMIT + 1` without OFFSET.

## Legacy cursor continuity

A valid `mrea.knowledge-cursor.v1` supplied to `failure_patterns_page()` remains on the exact historical grouped OFFSET query/order.

New traversals emit v2.

The query/filter fingerprint and committed snapshot binding remain unchanged.

## Tests added

`tests/test_failure_pattern_keyset_pagination.py` verifies:

1. v2 aggregate cursor emission;
2. complete grouped traversal without duplicates/gaps;
3. count-descending and deterministic tie continuation;
4. explicit NULL/empty-cause tie-breaking;
5. v2 continuation SQL has key predicates and no OFFSET;
6. v1 cursor remains on the legacy OFFSET path;
7. malformed aggregate keysets fail closed.

## Shared-contract impact

None.

No canonical fixture or shared schema change is required.

## Remaining intentional limitations

- materialized analytical aggregates;
- external client authn/authz;
- deployment/TLS/CORS/rate-limit policy;
- semantic/AI interpretation;
- field-device synchronization.

## Completion rule

Before final freeze:

1. inspect actual branch HEAD/diff;
2. require Chat-5 slice CI green;
3. require canonical contracts green;
4. require Chat4 generic CAD and Chat4→Chat5 integration gates green;
5. verify Round-4 runtime-truth regression remains present;
6. publish `ORCHESTRATOR_HANDOFF.md` as the final branch mutation;
7. verify CI on the final handoff HEAD.
