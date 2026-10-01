# Chat 3 — Ring 7 Implementation Report — Constraint Satisfaction Diagnostics

**Date:** 2026-09-30  
**Ring:** 7  
**Branch:** `chat-3/pass-7`  
**Base:** frozen Ring 6 head `28d4373b0e9cfdb25a1a833e9ca646c2a06f9d14`

## Objective

Add a read-only geometric satisfaction layer so a constraint candidate cannot be published if current geometry no longer satisfies that relation.

This is deliberately not a numerical solver: Ring 7 diagnoses; it does not move geometry.

## Delivered

### New module

`src/mrea_geometry/constraint_satisfaction.py`

Public types:

- `ConstraintSatisfaction`;
- `ConstraintSatisfactionAnalyzer`.

### Supported relation diagnostics

The analyzer covers the canonical v1 relation vocabulary used by Chat 3:

- COINCIDENT;
- HORIZONTAL;
- VERTICAL;
- PARALLEL;
- PERPENDICULAR;
- TANGENT;
- CONCENTRIC;
- EQUAL;
- SYMMETRIC.

### Residual semantics

Angular/axis relations use normalized residuals:

- HORIZONTAL: normalized vertical component;
- VERTICAL: normalized horizontal component;
- PARALLEL: normalized cross-product residual;
- PERPENDICULAR: normalized dot-product residual.

Default normalized tolerance:

`1e-3`

Linear/topological relations use mm residuals:

- EQUAL: line-length or round-radius delta;
- CONCENTRIC: center distance;
- COINCIDENT: minimum finite observable contact residual;
- TANGENT: line/round or round/round tangency residual, with finite segment and arc-span checks;
- SYMMETRIC: reflected-point/center residual plus equal-radius requirement for circles.

Default linear tolerance:

`0.05 mm`

### Resolver integration

`ConstraintResolver` now performs geometric satisfaction checking after entity-existence and confidence gates and before redundancy/verified-measurement conflict promotion.

If current geometry does not satisfy a candidate, it is not published. Instead it becomes canonical unresolved:

`UNSATISFIED_CONSTRAINT`

The message includes relation kind, residual, tolerance and residual unit.

### Truth invariant

Ring 7 does not alter:

- entity coordinates;
- verified measurement values;
- measurement provenance;
- measurement ids;
- canonical contract shape.

Invariant remains:

`verified physical measurement > image/geometry-derived relation`

### Public API / version

`ConstraintSatisfaction` and `ConstraintSatisfactionAnalyzer` are exported by `mrea_geometry`.

Package version is now:

`0.7.0`

New dependencies: **none**.

## Tests

New acceptance module:

`tests/test_constraint_satisfaction.py`

Coverage includes:

1. satisfied vs stale HORIZONTAL relation;
2. pure interior line crossing does not satisfy COINCIDENT;
3. valid vs stale LINE/CIRCLE tangency;
4. symmetry residual against explicit axis geometry;
5. resolver converts stale candidate to `UNSATISFIED_CONSTRAINT`;
6. normal generated rectangle candidates still resolve without new false unresolved items.

## GitHub Actions verification

Implementation head:

`8527a4ad9c711b18c6fc1bcd61dbfe537c6d53d5`

Workflow run:

`36645593928`

Authoritative Chat 3 result:

`56 passed in 0.44s`

Observed gates:

- Chat 3 / Geometry: SUCCESS;
- Contracts / canonical fixtures: SUCCESS;
- Chat 1: SUCCESS;
- Chat 2: SUCCESS;
- Chat 4 generic CAD: SUCCESS;
- Chat 5: SUCCESS;
- Integration / Chat 2 -> Chat 3: SUCCESS;
- Integration / Chat 3 -> Chat 4: FAIL only on frozen-worker ancestry's stale shared lookup `cad_verification_report["dimensions"]`.

The failing Chat 3 -> Chat 4 run reaches successful SketchPackage generation, schema validation, CAD transfer, CADPackage validation, CADVerificationReport validation and `overall_status == VERIFIED` before the stale lookup.

Current `main` already uses canonical:

`cad_verification_report["items"]`

Ring 7 does not modify Chat-6-owned shared integration infrastructure.

## Shared ownership

Ring 7 changes no files under:

- `core/contracts/`;
- canonical contract fixtures;
- `tests/integration/`;
- `.github/`;
- other chat directories.

## Known limitations / next work

Still deferred:

- numerical solving / entity movement;
- global over-constrained-system solving;
- richer uncertainty-aware tolerances;
- multi-view geometry relationships;
- CAD-native logic.

## Result

Ring 7 adds an explicit safety layer between relation detection and publication: candidate existence/confidence is no longer sufficient; current geometry must also satisfy the relation within defined tolerances.
