# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-01**
- Branch: `chat-5/pass-12`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 12**
- Central baseline checked before work: `main` @ `c888704b37e88b68c055f1095e6e9a4fc3650f7e`
- Central state at start: **Round 11 closed/accepted; Chat 5 Pass 11 integrated/green; next full worker pass ready**
- Tested implementation SHA: `0e4b2df0b144fe7116b7e94141be85266a0820fc`
- MREA CI: `36802306777` — **SUCCESS**
- Chat-5 test result: **72 passed in 11.64s**
- State: **Pass 12 implementation verified; documentation published; final handoff/freeze pending**

## Baseline discipline

Pass 12 was branched directly from the then-current shared `main` rather than from `chat-5/pass-11` history.

This preserves central Round-11 integration/control changes and prevents a worker-local replay from overwriting newer shared state.

No file outside `chat_5_lifecycle_engineering_knowledge/` is modified by Pass 12.

## Preserved truths

Unchanged:

- revision/manufacturing/physical-instance lifecycle semantics;
- Round-4 numerical-vs-runtime verification separation;
- runtime fail-closed manufacturing eligibility;
- authoritative SQLite snapshot + normalized relational projection;
- stale-writer protection and transactional rollback;
- backup/restore/read-only consistency checks;
- deterministic engineering knowledge semantics;
- v2 keyset cursor ordering/fingerprint/snapshot binding;
- v1 cursor continuity;
- GET-only HTTP surface and optional HMAC cursor wrapper;
- shared canonical contracts.

## Pass 12 architecture

### Schema migration v4

`SQLITE_RELATIONAL_SCHEMA_VERSION` is now `4`.

Migration `materialized_engineering_knowledge` adds:

```text
lifecycle_revision_outcomes_materialized
lifecycle_failure_patterns_materialized
```

Migration invalidates the previous read-model version (`snapshot_version = -1`) so opening an existing v3 database deterministically rebuilds the normalized projection and the new aggregates before it can be served as current.

### Atomic refresh

The materialized tables are refreshed by a SQLite trigger attached to the publication update of `lifecycle_read_model_meta.snapshot_version`.

Existing persistence order is preserved:

```text
authoritative snapshot write
→ normalized read-model replace
→ publish read_model snapshot_version
→ trigger rebuilds materialized aggregates
→ transaction commit
```

The trigger executes inside the same transaction. There is no separately committed cache epoch and no possibility for `SQLiteLifecycleReadOnlySession` to accept a materialized generation different from the committed normalized snapshot generation.

### Materialized repository

Added `SQLiteMaterializedEngineeringKnowledgeRepository`, extending the existing keyset repository rather than replacing factual definitions.

Materialized paths:

- `revision_outcomes()`;
- `revision_outcomes_page()` for new/v2 traversal;
- `failure_patterns()`;
- `failure_patterns_page()` for new/v2 traversal.

Unchanged paths remain inherited.

### Legacy cursor compatibility

For `mrea.knowledge-cursor.v1`, the materialized repository delegates to the exact previous raw OFFSET implementation. This is deliberate: issued cursors retain historical execution/order semantics instead of being silently translated into a different continuation model.

New/no-cursor traversal emits/uses v2 state against materialized rows.

## Semantic equivalence checks

`tests/test_materialized_knowledge.py` verifies:

1. materialized revision outcomes equal the pre-existing raw aggregate semantics;
2. materialized failure patterns equal the pre-existing raw aggregate semantics;
3. GLOBAL, PART and REVISION scopes are generated;
4. new/v2 pages read materialized tables and do not perform raw grouped aggregation;
5. v1 failure-pattern cursor remains on historical raw OFFSET path;
6. a later lifecycle commit atomically refreshes aggregate counts and snapshot version.

Existing Pass-10.1 SQL-shape regression was retargeted from the old raw revision table alias to the new materialized execution surface while preserving the original invariant: v2 continuation has key predicates and no OFFSET.

## Verification

Tested implementation SHA:

```text
0e4b2df0b144fe7116b7e94141be85266a0820fc
```

Workflow:

```text
MREA CI / 36802306777
```

Results:

- `Chat 5 / Lifecycle` — **SUCCESS**, `72 passed in 11.64s`;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**;
- Chat 1–3 unit jobs — **SUCCESS**;
- unrelated integration jobs — skipped by existing branch filters.

## Shared-contract impact

None.

No change to `core/contracts/**`, canonical fixtures, root integration tests, workflows, or Chat 1–4 code is required.

## External runtime truth

Unchanged:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Remaining intentional limitations

- external client authn/authz;
- deployment/TLS/CORS/rate-limit policy;
- semantic/AI interpretation;
- field-device synchronization.

## Freeze rule

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation for Pass 12. After that commit, `chat-5/pass-12` is frozen. Final CI is verified on that exact branch HEAD without a follow-up documentation-only mutation.
