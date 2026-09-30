# Chat 3 — Ring 9 Implementation Report — Global Constraint-Set Diagnostics

**Date:** 2026-09-30  
**Ring:** 9  
**Branch:** `chat-3/pass-9`  
**Base:** frozen Ring 8 head `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`

## Objective

Add the first global constraint-set diagnostic layer after Rings 4–8 established candidate generation, satisfaction checks and residual-aware confidence.

Ring 9 detects graph-level contradictions and safe transitive redundancies without moving geometry or claiming full solver capability.

## Delivered

### New module

`src/mrea_geometry/constraint_system.py`

Public API:

- `ConstraintSystemAnalysis`;
- `ConstraintSystemAnalyzer`.

### Orientation parity graph

The analyzer processes:

- `HORIZONTAL`;
- `VERTICAL`;
- `PARALLEL`;
- `PERPENDICULAR`.

A parity-aware disjoint-set represents orientation equivalence modulo 90 degrees.

It classifies each accepted resolver constraint as:

- independent and retained;
- provably redundant and omitted;
- contradictory and converted to unresolved.

### Evidence ordering

Deterministic priority is:

1. confidence descending;
2. `DETECTED` before `INFERRED`;
3. direct axis relations before pair relations at equal evidence strength;
4. `constraint_id` tie-breaker.

This makes the fail-closed choice reproducible and prevents weaker evidence from silently replacing stronger evidence.

### Conflict output

A contradictory orientation relation becomes:

`OVERCONSTRAINED_ORIENTATION_CONFLICT`

The rejected constraint is not published in the canonical SketchPackage.

### Transitive redundancy

Safe union-find reduction also applies independently to:

- `EQUAL`;
- `CONCENTRIC`.

No unsafe transitivity is assumed for `COINCIDENT`, `TANGENT` or `SYMMETRIC`.

### Pipeline integration

`VisionGeometryPipeline` now executes:

```text
geometry candidate extraction
-> GeometryPipeline
-> ConstraintResolver
-> ConstraintSystemAnalyzer
-> SketchPackageBuilder
```

Existing resolver issues are preserved and global contradiction issues are appended before canonical package construction.

### Shared contract impact

None.

`SketchPackage v1` remains unchanged. Ring 9 uses the existing canonical `unresolved` mechanism.

## Tests

New module:

`tests/test_constraint_system.py`

Coverage includes:

1. consistent orientation chain with one transitive redundant relation;
2. fail-closed conflicting orientation relation;
3. `DETECTED` relation winning over equal-confidence `INFERRED` conflict;
4. transitive `PARALLEL` cycle reduction;
5. transitive `EQUAL` cycle reduction;
6. non-graph relation preservation;
7. existing resolver issue preservation;
8. deterministic result under reversed input order.

## Runtime / dependencies

Package version:

`0.9.0`

New Ring 9 dependencies: **none**.

## GitHub Actions verification

Implementation head:

`7b317e0c0a3e7c5f69000f8c51dd47adff362aa6`

Workflow run:

`36652647774`

Observed results:

- Chat 3 / Geometry: **SUCCESS — 73 passed in 0.46s**;
- Contracts / canonical fixtures: **SUCCESS**;
- Chat 1 / Capture: **SUCCESS**;
- Chat 2 / Measurement: **SUCCESS**;
- Chat 4 / Generic CAD gate: **SUCCESS**;
- Chat 5 / Lifecycle: **SUCCESS**;
- Integration / Chat 2 -> Chat 3: **SUCCESS**.

### Chat 3 -> Chat 4 inherited baseline issue

The frozen worker ancestry still contains the old Chat-6-owned lookup:

```python
transfer.cad_verification_report["dimensions"]
```

The boundary test reaches successful SketchPackage generation, canonical validation, CAD transfer, CADPackage validation, CADVerificationReport validation and `overall_status == "VERIFIED"`, then raises `KeyError: 'dimensions'`.

Current `main` uses canonical:

```python
transfer.cad_verification_report["items"]
```

Ring 9 does not backport or modify shared integration infrastructure.

## Truth hierarchy

Unchanged:

```text
verified physical measurement > geometry/image-derived relation
```

The analyzer never moves entities and never rewrites verified measurements.

## Limitations / deferred work

Still deferred:

- full numerical constraint solving/entity movement;
- complete degrees-of-freedom accounting;
- nonlinear/global geometric consistency beyond the proven graph subset;
- uncertainty propagation from calibration/vision into tolerance selection;
- multi-view geometry relationships;
- CAD-native logic.

## Result

Ring 9 adds a deterministic pre-solver safety layer:

```text
independent relation -> retain
provably redundant relation -> omit
provably contradictory orientation relation -> explicit unresolved
```

This reduces overconstraint risk without pretending the system has a full CAD solver.
