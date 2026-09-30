# ORCHESTRATOR HANDOFF — Chat 5 / Pass 8 / Round 4 FIX_REQUIRED correction

**Directive:** `OD-2026-09-30-004` + `ORCHESTRATOR_FIX_REQUIRED_ROUND4_001.md`  
**Branch:** `chat-5/pass-8`  
**Original frozen Pass-8 handoff:** `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`  
**Chat-6 reopen commit:** `e6b46bf0d3be0b0b20289a540bb58ffaa72a9f6e`  
**Corrected implementation SHA tested before this handoff:** `d839044c56cd6b9da6c0764662d30ed9e5ca6f05`  
**Implementation CI:** `MREA CI / 36759137105` — **SUCCESS**  
**Status:** FIX_REQUIRED correction implemented; this handoff re-freezes `chat-5/pass-8`.

## Correction delivered

Chat 5 now preserves CAD runtime verification truth independently from canonical numerical verification.

`CADRevisionPreparationService.prepare(...)` accepts optional vendor-neutral `runtime_evidence` mapping using schema:

```text
mrea.cad-runtime-evidence.v1
```

Retained lifecycle provenance:

- runtime status: `VERIFIED | FAILED | UNVERIFIED`;
- runtime evidence schema version;
- `real_host_executed` boolean;
- adapter identity and CAD/sketch package identity are validated against the canonical CAD package before the revision is accepted.

No dependency on Chat 4 Python classes was introduced.

## Manufacturing fail-closed rule

For `CAD_TRANSFER` revisions:

```text
canonical numerical verification != VERIFIED
→ manufacturing blocked

runtime evidence supplied AND runtime status != VERIFIED
→ manufacturing blocked

runtime status == VERIFIED AND real_host_executed != true
→ revision preparation rejected
```

A numerical `VERIFIED` report never upgrades `UNVERIFIED` runtime evidence.

Backward compatibility is preserved: existing generic/test-double CAD flows that do not supply a runtime-evidence gate continue to use the prior canonical verification rule.

## Persistence and read model

Runtime truth is preserved through:

- authoritative JSON snapshot serialization/hydration;
- SQLite reopen;
- normalized relational read model;
- `revision_history()` query results.

Relational schema migration advanced from version 2 to version 3:

```text
3 / cad_runtime_truth
```

New nullable read-model columns on `lifecycle_revisions`:

- `runtime_status`;
- `runtime_evidence_schema_version`;
- `runtime_real_host_executed`.

Legacy snapshots and pre-v3 databases remain readable; absent runtime evidence hydrates as `None` and migration/backfill preserves existing lifecycle truth.

## Deterministic tests added/updated

Added `tests/test_round4_runtime_truth.py`, covering:

1. canonical numerical VERIFIED + runtime UNVERIFIED is manufacturing-ineligible;
2. blocked manufacturing produces no mutation;
3. runtime truth survives normalized read model and SQLite reopen;
4. canonical numerical FAILED + runtime UNVERIFIED remains ineligible;
5. runtime FAILED and UNVERIFIED fail closed;
6. explicit runtime VERIFIED requires `real_host_executed=true`;
7. valid runtime VERIFIED + real host execution is eligible;
8. generic verified CAD flow with no runtime evidence remains backward compatible.

Updated persistence/backup/read-only tests for relational schema v3.

## CI evidence

Exact pre-handoff tested implementation:

```text
d839044c56cd6b9da6c0764662d30ed9e5ca6f05
```

Workflow:

```text
MREA CI / 36759137105
```

Results:

- `Chat 5 / Lifecycle` — **SUCCESS**, `47 passed in 1.80s`;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**, `2 passed, 1 warning in 0.48s`.

The integration warning is the pre-existing Chat 4 `TestDoubleCadAdapter` pytest collection warning and is outside Chat 5 ownership.

The special central `Integration / Round 4 Chat 4 -> Chat 5 truth` gate is owned by central orchestration and must be rerun against the corrected worker cut during candidate reconciliation.

## Files changed by this correction

Relative to Chat-6 reopen SHA `e6b46bf0d3be0b0b20289a540bb58ffaa72a9f6e`:

Modified:

- `src/mrea_lifecycle/__init__.py`;
- `src/mrea_lifecycle/models.py`;
- `src/mrea_lifecycle/persistence.py`;
- `src/mrea_lifecycle/relational.py`;
- `src/mrea_lifecycle/services.py`;
- `src/mrea_lifecycle/sqlite_schema.py`;
- `tests/test_backup_readonly.py`;
- `tests/test_relational_persistence.py`;
- `ORCHESTRATOR_HANDOFF.md`.

Added:

- `tests/test_round4_runtime_truth.py`.

No correction files were changed outside `chat_5_lifecycle_engineering_knowledge/`.

## Ownership / contract boundary

Unchanged:

- shared canonical contracts and fixtures;
- canonical `mrea.lifecycle-event.v1`;
- Chat 1-4 source files;
- root integration tests;
- CI workflow definitions;
- existing Pass-8 pagination behavior.

No shared-contract change request is required.

## Freeze

Publishing this handoff is the final Chat-5 worker action for `ORCHESTRATOR_FIX_REQUIRED_ROUND4_001.md` and re-freezes `chat-5/pass-8`. Any further worker change requires a new explicit `FIX_REQUIRED` or directive in the repository.
