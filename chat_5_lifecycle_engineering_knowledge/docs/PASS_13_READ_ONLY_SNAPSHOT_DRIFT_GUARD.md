# Pass 13 — Read-Only Snapshot Drift Guard

## Problem

The read-only lifecycle session accepted a committed generation when it opened, but the raw SQLite connection remained in autocommit mode.

A later writer commit could therefore become visible to a subsequent SELECT on the same connection while the session still exposed the generation captured at open time.

The invalid state was:

```text
session.snapshot_version = N
query rows = generation N+1
```

That breaks the meaning of snapshot-bound knowledge cursors and any response that labels rows with the session generation.

## Required invariant

A read-only session must never silently return facts from a generation other than the generation it accepted at open time.

If the underlying committed generation advances, the session must fail closed until the caller explicitly refreshes/reopens it.

## Implementation

`_SnapshotGuardedConnection` wraps repository SQL execution. It records the accepted:

```text
snapshot schema version
authoritative snapshot version
read-model snapshot version
relational schema version
```

Before every repository statement it rereads persistence metadata and requires exact equality.

`_SnapshotGuardedCursor` repeats that validation after rows are fetched. This prevents successful delivery when a writer advances the generation between the pre-query guard and row consumption.

Drift raises:

```text
LifecycleReadOnlyStaleError
```

and explicitly instructs the caller to refresh.

## Why not pin a SQLite read transaction

A long-lived read transaction would provide a stable SQLite snapshot but would also keep a read lock alive between application calls. The current store does not depend on WAL mode, so this can block a writer commit in rollback-journal mode.

Pass 13 keeps the existing short/autocommit read model and adds generation validation instead. An idle reader does not prevent the writer from advancing; it simply cannot continue reading under its old generation label afterwards.

## Refresh semantics

`SQLiteLifecycleReadOnlySession.refresh()` remains the explicit generation boundary:

```text
old session generation N
→ external writer commits N+1
→ next read: LifecycleReadOnlyStaleError
→ refresh()
→ session accepts N+1
→ reads resume
```

## Scope

Covered repository surfaces:

- normalized lifecycle queries;
- materialized engineering knowledge queries;
- inherited keyset/raw knowledge queries because they use the same guarded execute facade.

Unchanged:

- schema v4;
- domain events and lifecycle state machine;
- CAD verification/runtime truth;
- manufacturing eligibility;
- cursor formats v1/v2;
- HTTP API schema;
- shared contracts.

## Verification

Implementation SHA:

```text
a26c1d8f6927e3ebdfcf69d7f759893cd7b139bd
```

CI:

```text
MREA CI 36806176020 — SUCCESS
Chat 5: 73 passed in 3.05s
Contracts: SUCCESS
Chat 4 generic: SUCCESS
Chat 4 -> Chat 5: SUCCESS
```
