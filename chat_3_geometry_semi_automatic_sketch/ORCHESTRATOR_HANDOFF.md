# ORCHESTRATOR HANDOFF — Chat 3 — Pass 4

**From:** Chat 3 — Geometry & Semi-Automatic Sketch  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Pass / Ring:** 4  
**Branch:** `chat-3/pass-4`  
**Branch base:** frozen Ring 3 head `08e716161a8c9173b7583d6ad87c84c10ddc4221`  
**Implementation/docs head before handoff commit:** `92494b35db6c1ef9ee58ae04910a55c3434a5cc3`  
**Date:** 2026-09-29

## Authorization note

At Pass 4 start, current `main` still exposed `OD-2026-09-29-003`; no Chat 6 `OD-004` or `chat-3/pass-4` branch existed.

The user explicitly instructed Chat 3 to start **Pass / Ring 4**. To avoid losing the frozen Ring 3 implementation while also avoiding changes to stale `main`, this branch was created directly from Ring 3 final head.

No shared contracts, shared CI, integration tests, or other chat-owned files were modified.

## Status

`READY_FOR_RING4_INTEGRATOR_REVIEW_WITH_PREEXISTING_CHAT3_TO_CHAT4_GATE_DEFECT`

## Delivered functionality

Ring 4 implements the previously missing Chat 3 constraint-resolution / promotion layer.

### ConstraintResolver

New module:

`src/mrea_geometry/constraints.py`

New public types:

- `ResolvedConstraint`;
- `ConstraintIssue`;
- `ConstraintResolution`;
- `ConstraintResolver`.

The resolver does not move geometry. It decides which already-observed candidate relations may be safely published to canonical `SketchPackage v1`.

### Truth hierarchy

The invariant remains:

```text
verified physical measurement > image-derived / geometry-derived relation
```

Verified dimension values are never changed to satisfy a relation.

### Promotion gates

A constraint candidate is published only when:

1. all referenced entities exist;
2. effective confidence is at least the promotion threshold;
3. the relation is not redundant with stronger axis relations;
4. the relation does not contradict verified measurements.

Default promotion threshold:

```text
0.95
```

Effective confidence:

```text
min(candidate confidence, confidence of every referenced entity that exposes confidence)
```

### Explicit unresolved states

Ring 4 adds explicit relation-level failure codes including:

```text
CONSTRAINT_ENTITY_MISSING
CONSTRAINT_BELOW_PROMOTION_CONFIDENCE
VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT
VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT
```

Rejected relations do not disappear silently.

### Measurement guardrails

`EQUAL` is suppressed when verified comparable intrinsic measurements disagree beyond tolerance.

`CONCENTRIC` is suppressed when a verified non-zero center-distance measurement contradicts concentricity.

### Redundancy / overconstraint control

For axis-aligned geometry:

- HORIZONTAL / VERTICAL are publishable;
- PARALLEL already implied by matching axis constraints is omitted;
- PERPENDICULAR already implied by HORIZONTAL + VERTICAL is omitted.

For rotated geometry, non-redundant PARALLEL / PERPENDICULAR relations remain publishable.

### Canonical builder integration

`SketchPackageBuilder.build()` now accepts optional `constraint_resolution`.

Backward compatibility is preserved:

```text
constraint_resolution omitted -> constraints = []
```

Therefore the accepted Ring 1 canonical fixture remains unchanged.

### Constraint-aware vision composition

New module:

`src/mrea_geometry/vision_pipeline.py`

The package-level `VisionGeometryPipeline` now composes:

```text
ImageGeometryExtractor result
→ GeometryPipeline
→ ConstraintResolver
→ SketchPackageBuilder
→ extraction unresolved merge
```

Ring 3 detector logic remains unchanged.

### Vision golden behavior

Current front-plate golden publishes six safe inferred constraints:

- EQUAL opposite horizontal sides;
- EQUAL opposite vertical sides;
- HORIZONTAL bottom/top;
- VERTICAL left/right.

The two detected hole circles each have vision confidence `0.766`; therefore their EQUAL relation is **not** promoted at a `0.95` threshold.

It is explicit in canonical `unresolved` as:

```text
CONSTRAINT_BELOW_PROMOTION_CONFIDENCE
```

Verified dimensions remain unchanged:

- width `40.0 mm`;
- height `20.0 mm`;
- hole diameter `8.0 mm`;
- center distance `20.0 mm`.

## Runtime / dependencies

Package version:

```text
0.4.0
```

New dependencies in Ring 4: **none**.

Ring 3 OpenCV dependency remains unchanged.

## GitHub Actions verification

Authoritative implementation-head run:

```text
run: 36625586757
head: 8ca1fa2294467636583eea2340c2c02e7d130cf7
```

Results:

- `Chat 3 / Geometry`: **SUCCESS — 35 passed in 0.31s**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- `Chat 2 / Measurement`: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: **SUCCESS**;
- `Chat 4 / Generic CAD gate`: **SUCCESS**;
- `Integration / Chat 3 -> Chat 4`: **FAIL — pre-existing orchestrator-owned stale field lookup**.

## External Chat 3 -> Chat 4 gate defect

The integration test successfully:

1. builds Chat 3 `SketchPackage`;
2. validates it against canonical schema;
3. executes Chat 4 CAD transfer;
4. validates `CADPackage`;
5. validates `CADVerificationReport`;
6. confirms `overall_status == VERIFIED`.

It then fails with:

```text
KeyError: 'dimensions'
```

because the shared test reads:

```python
transfer.cad_verification_report["dimensions"]
```

while canonical `CADVerificationReport v1` exposes:

```python
transfer.cad_verification_report["items"]
```

This defect is unchanged from Ring 3. Chat 3 did not modify the Chat 6-owned integration test.

## Requested Chat 6 actions

1. Review Pass 4 constraint-promotion behavior.
2. Correct/reclassify the shared Chat 3 -> Chat 4 test field:

```text
"dimensions" -> "items"
```

3. Re-run full integration CI on the assembled baseline.
4. Publish an explicit Pass 4 verdict / next directive.

## Shared ownership / Change Requests

Shared contracts changed: **none**.  
Shared canonical fixtures changed: **none**.  
Shared integration tests changed: **none**.  
CI changed: **none**.  
Other chat directories changed: **none**.  
Change Requests: **none**.

## Known limitations / next owned slice

Still deferred:

- numerical constraint solving / entity movement;
- COINCIDENT/TANGENT/SYMMETRIC generation policy;
- Dimensioned View renderer;
- multi-view geometry/constraints;
- CAD-native logic.

Unless Chat 6 issues another priority, the next natural Chat 3 vertical slice is **Dimensioned View**.

## Branch freeze

This handoff is the final worker commit for Ring 4.

After publication, `chat-3/pass-4` is treated as **frozen** pending Chat 6 verdict or explicit user/orchestrator instruction.
