# Chat 3 — Pass 10.1 — Post-Selected-Cut Manifest

**Date:** 2026-09-30  
**Current central directive:** `OD-2026-09-30-004`  
**Selected Round-4 cut:** `chat-3/pass-8` @ `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`  
**Latest frozen worker implementation cut:** `chat-3/pass-10` @ `01df10c2fff8d00ae1490405961773dd4e543b5a`

## Purpose

This manifest enumerates every repository path changed between the Chat-6-selected Pass 8 cut and the later user-directed Pass 10 cut.

It is **not an authorization to replay these files**. It exists so Chat 6 can review later work without importing stale worker ancestry or guessing which files belong to which layer.

## Exact GitHub compare

```text
base    d786e1d49b5c8f2837a3ce936f7f1c0d93336d49
head    01df10c2fff8d00ae1490405961773dd4e543b5a
status  ahead
ahead   19 commits
files   13
```

## Runtime / package paths

### `chat_3_geometry_semi_automatic_sketch/src/mrea_geometry/constraint_system.py`

- Added in Pass 9.
- Owner: Chat 3.
- Role: global retained-constraint diagnostics and safe transitive reduction.
- Dependency: Pass 8 resolver/confidence/satisfaction semantics.
- Replay priority: **Pass 9 first**.

### `chat_3_geometry_semi_automatic_sketch/src/mrea_geometry/dof_audit.py`

- Added in Pass 10.
- Owner: Chat 3.
- Role: structural DOF lower-bound audit.
- Dependency: globally filtered Pass 9 `ConstraintResolution`.
- Replay priority: **after Pass 9**.

### `chat_3_geometry_semi_automatic_sketch/src/mrea_geometry/vision_pipeline.py`

- Modified across Pass 9 and Pass 10.
- Pass 9 adds `ConstraintSystemAnalyzer` to build-sketch flow.
- Pass 10 adds `StructuralDofAnalyzer` and `audit_structural_dof(...)`.
- Must be replayed incrementally, not copied wholesale across a changing central baseline.

### `chat_3_geometry_semi_automatic_sketch/src/mrea_geometry/__init__.py`

- Modified across Pass 9 and Pass 10.
- Adds public exports for the two post-cut diagnostic layers.
- Replay after the corresponding implementation modules are accepted.

### `chat_3_geometry_semi_automatic_sketch/pyproject.toml`

- Version advances from selected-cut package level to `0.10.0` by Pass 10.
- No new post-Pass-8 dependency is introduced.
- Version should be reconciled by Chat 6 after deciding which layers are accepted.

## Test paths

### `chat_3_geometry_semi_automatic_sketch/tests/test_constraint_system.py`

- Added in Pass 9.
- Covers orientation conflict/redundancy/evidence-order semantics.
- Must accompany any accepted replay of `constraint_system.py`.

### `chat_3_geometry_semi_automatic_sketch/tests/test_dof_audit.py`

- Added in Pass 10.
- Covers structural parameter/equation budgets and fail-closed classification.
- Depends logically on Pass 9 integration order even though most unit tests are isolated.

## Worker documentation paths

### Pass 9 docs

- `docs/BUILD_REUSE_CHECK_RING9_GLOBAL_CONSTRAINT_DIAGNOSTICS.md`
- `docs/IMPLEMENTATION_REPORT_RING9_GLOBAL_CONSTRAINT_DIAGNOSTICS_2026-09-30.md`

### Pass 10 docs

- `docs/BUILD_REUSE_CHECK_RING10_STRUCTURAL_DOF_AUDIT.md`
- `docs/IMPLEMENTATION_REPORT_RING10_STRUCTURAL_DOF_AUDIT_2026-09-30.md`

### Cumulative worker state

- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

These cumulative files describe later worker history and must not overwrite current-main orchestration truth. Chat 6 should selectively preserve useful worker evidence while retaining the current `ORCHESTRATOR_DIRECTIVE.md` from `main`.

## Files explicitly NOT present in the Pass 8 -> Pass 10 delta

The later Chat 3 worker stack does **not** modify:

- `.github/workflows/*`;
- `core/contracts/*`;
- shared canonical contract fixtures;
- `tests/integration/*`;
- any Chat 1 / Chat 2 / Chat 4 / Chat 5 runtime path;
- Chat 6 orchestration files.

This is important because the stale shared `cad_verification_report["dimensions"]` integration test observed on later worker branches comes from ancestry, not from a Chat-3-owned post-Pass-8 delta.

## Recommended future replay groups

### Group A — Pass 9 functional replay

```text
constraint_system.py
test_constraint_system.py
vision_pipeline.py (Pass 9 portion only)
__init__.py (Pass 9 exports only)
Pass 9 docs as evidence
```

Then run on current main:

```text
Chat 3 / Geometry
Contracts
Integration / Chat 2 -> Chat 3
Integration / Chat 3 -> Chat 4
```

### Group B — Pass 10 functional replay

Only after Group A acceptance:

```text
dof_audit.py
test_dof_audit.py
vision_pipeline.py (Pass 10 additive API portion)
__init__.py (Pass 10 exports)
Pass 10 docs as evidence
```

Then rerun the same gates.

## Pass 10.1 files

Pass 10.1 itself is reconciliation-only and should remain distinguishable from deferred runtime work. Its expected worker-owned delta is documentation/state/handoff only.

## Central decision boundary

Until Chat 6 explicitly changes the directive:

```text
PASS_8  = SELECTED_FOR_ROUND4_STAGE1
PASS_9  = DEFERRED
PASS_10 = DEFERRED
PASS_10_1 = RECONCILIATION_ONLY
```
