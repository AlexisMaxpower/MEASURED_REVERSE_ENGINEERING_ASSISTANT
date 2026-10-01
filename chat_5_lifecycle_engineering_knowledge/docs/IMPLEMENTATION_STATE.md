# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-01**
- Branch: `chat-5/pass-13`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 13**
- Central baseline checked before work: `main` @ `4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`
- Central state at start: **Round 12 closed/accepted; next full worker pass ready**
- Tested implementation SHA: `a26c1d8f6927e3ebdfcf69d7f759893cd7b139bd`
- MREA CI: `36806176020` — **SUCCESS**
- Chat-5 test result: **73 passed in 3.05s**
- State: **Pass 13 worker implementation verified and handed to central integration**

## Baseline discipline

Pass 13 was branched directly from the then-current shared `main`. No historical Chat-5 worker branch was used as a baseline.

All implementation changes remain under `chat_5_lifecycle_engineering_knowledge/`.

## Root cause closed in Pass 13

`SQLiteLifecycleReadOnlySession` previously validated this invariant only at open time:

```text
authoritative snapshot version == normalized read-model version
```

The underlying SQLite handle used autocommit. Across separate SELECT statements, an already-open connection could observe a later writer commit. The Python session object would still retain its old `snapshot_version`, so a later knowledge/lifecycle query could return newer rows under an older generation label.

That is incompatible with the existing snapshot-bound cursor/read contract.

## Pass 13 architecture

### Snapshot-guarded connection facade

The session now injects `_SnapshotGuardedConnection` into both SQL repository surfaces.

For every repository `execute()` it validates:

- lifecycle snapshot schema version;
- authoritative `lifecycle_store.version`;
- `lifecycle_read_model_meta.snapshot_version`;
- current relational migration version.

The metadata must still equal the generation accepted when the session opened.

### Post-fetch validation

`_SnapshotGuardedCursor` checks the same generation after `fetchone()` and `fetchall()`.

This closes the window where a generation could advance after the pre-statement check but before rows are returned to the caller. Drift raises `LifecycleReadOnlyStaleError`; callers must use `refresh()` or open a new session.

### No long-lived read transaction

Pass 13 does not pin the session with `BEGIN`.

Reason: the current store does not require WAL mode. In the default rollback-journal model, keeping a read transaction open across application calls can block writer commit. The guard keeps completed reads short and lets the writer advance; the old session then fails closed on its next read.

### No schema / contract change

No SQLite migration is added. `SQLITE_RELATIONAL_SCHEMA_VERSION` remains `4`.

No shared contract, canonical fixture, HTTP schema, cursor encoding, lifecycle domain rule or manufacturing eligibility rule changes.

## Regression coverage

`tests/test_read_only_snapshot_guard.py` verifies one open session across an external commit:

1. session opens on R1 and reads both lifecycle query and materialized knowledge surfaces;
2. a separate writer successfully commits R2 while the reader object remains open;
3. the old session rejects both query surfaces with `LifecycleReadOnlyStaleError`;
4. the cached session generation does not silently advance;
5. explicit `refresh()` accepts the next generation;
6. both query surfaces then return R1 and R2.

## Verification

Tested implementation SHA:

```text
a26c1d8f6927e3ebdfcf69d7f759893cd7b139bd
```

Workflow:

```text
MREA CI / 36806176020 — SUCCESS
```

Results:

- `Chat 5 / Lifecycle` — **SUCCESS**, `73 passed in 3.05s`;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**;
- Chat 1–3 unit jobs — **SUCCESS**;
- unrelated integration jobs — skipped by existing branch filters.

## Shared-contract impact

None.

## Standing SOLIDWORKS host qualification

Real-host SOLIDWORKS qualification is not a Chat-5 or per-round status field. The operational authority is the dedicated standing workflow:

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

Chat 5 preserves runtime evidence (`VERIFIED | FAILED | UNVERIFIED`) on individual CAD/lifecycle records, but it does not infer or mirror the standing host qualification. When host qualification matters, resolve it from the dedicated workflow artifact and its host-boundary fingerprint.

## Remaining intentional limitations

- external client authn/authz;
- deployment/TLS/CORS/rate-limit policy;
- semantic/AI interpretation;
- field-device synchronization.

## Freeze rule

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation for Pass 13. After that commit, `chat-5/pass-13` is frozen. Central integration/final certification may correct integration documentation without reopening worker feature scope.
