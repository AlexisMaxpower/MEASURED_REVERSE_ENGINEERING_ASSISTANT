# Chat 3 — Ring 10 Implementation Report — Structural DOF Audit

**Date:** 2026-09-30  
**Ring:** 10  
**Branch:** `chat-3/pass-10`  
**Base:** frozen Ring 9 head `0b657c07cc6d325be8e813c565fe5ca6bcad309a`

## Objective

Add a truthful pre-solver degrees-of-freedom diagnostic that can prove some sketches are still underconstrained without claiming numerical solver capability that Chat 3 does not yet have.

## Delivered

### New module

`src/mrea_geometry/dof_audit.py`

Public API:

- `StructuralDofAudit`;
- `StructuralDofAnalyzer`.

### Exact primitive parameter count

Ring 10 counts the current internal parameterization exactly:

- POINT -> 2;
- LINE -> 4;
- CIRCLE -> 3;
- ARC -> 5.

### Conservative equation budget

For each globally retained constraint, the analyzer uses a safe maximum scalar-equation contribution:

- HORIZONTAL / VERTICAL / PARALLEL / PERPENDICULAR / TANGENT / EQUAL -> 1;
- CONCENTRIC -> 2;
- COINCIDENT -> 2;
- SYMMETRIC -> 3.

Each bound dimension contributes at most one additional scalar equation.

### Safe lower-bound semantics

```text
remaining_dof_lower_bound = max(
    0,
    parameter_count - total_equation_upper_bound,
)
```

If this lower bound is positive, the sketch is definitely underconstrained even if every counted equation were independent.

If it is zero, Ring 10 returns `NOT_PROVEN_UNDERCONSTRAINED`; it deliberately does not claim `FULLY_CONSTRAINED`, because equation dependence/degeneracy requires a numerical rank/solver analysis.

Unknown future constraint kinds fail closed with:

`INDETERMINATE_UNKNOWN_CONSTRAINT_ARITY`

and no DOF lower bound is asserted.

### Pipeline integration

`VisionGeometryPipeline.audit_structural_dof(extraction, context)` now exposes the diagnostic through the existing image-derived path:

```text
GeometryPipeline
-> ConstraintResolver
-> ConstraintSystemAnalyzer
-> StructuralDofAnalyzer
```

The existing `build_sketch()` output is unchanged. `SketchPackage v1` and the Chat 3 -> Chat 4 contract are not modified.

## Tests

New acceptance module:

`tests/test_dof_audit.py`

Coverage includes:

1. lone point -> provable 2 remaining DOF;
2. line + horizontal + one dimension remains provably underconstrained;
3. concentric/equal circle equation budgets;
4. equation budget equal to parameter count does not claim fully constrained;
5. conservative symmetry equation upper bound;
6. unknown future constraint kind fails closed;
7. all v1 primitive parameter counts;
8. deterministic output under entity/constraint/dimension reordering.

## Runtime / dependencies

Package version:

`0.10.0`

New Ring 10 dependencies: **none**.

## GitHub Actions verification

Authoritative code + tests + Build/Reuse head:

`77ca90a17b8b9bdc60c5cbade996b5bd412364a9`

Workflow run:

`36659318018`

Observed results:

- Chat 3 / Geometry: **SUCCESS — 81 passed in 0.50s**;
- Contracts / canonical fixtures: **SUCCESS**;
- Chat 1 / Capture: **SUCCESS**;
- Chat 2 / Measurement: **SUCCESS**;
- Chat 4 / Generic CAD gate: **SUCCESS**;
- Chat 5 / Lifecycle: **SUCCESS**;
- Integration / Chat 2 -> Chat 3: **SUCCESS**.

### Chat 3 -> Chat 4 inherited baseline issue

The frozen worker ancestry still carries the older Chat-6-owned integration test lookup:

```python
transfer.cad_verification_report["dimensions"]
```

The run reaches successful SketchPackage generation, CAD transfer and schema validation, then fails with `KeyError: 'dimensions'`.

Current `main` uses canonical `cad_verification_report["items"]`; Ring 10 does not backport shared integration infrastructure.

## Shared contract impact

None.

No Ring 10 changes to:

- `core/contracts/`;
- canonical shared fixtures;
- repository integration tests;
- CI workflow;
- other chat directories.

## Limitations / deferred work

Still deferred:

- numerical Jacobian-rank DOF proof;
- actual constraint solving / entity movement;
- nonlinear/global geometric consistency beyond Ring 9 graph proofs;
- uncertainty propagation from calibration/vision into tolerance selection;
- multi-view geometry relationships;
- CAD-native logic.

## Result

Ring 10 introduces a truthful pre-solver question the system can now answer:

```text
Can this sketch possibly be fully constrained with the currently retained
constraints and dimensions?
```

If the answer is mathematically "no", Chat 3 can prove underconstraint. If the simple equation budget is sufficient, Chat 3 explicitly defers the stronger conclusion to a future numerical rank/solver layer.
