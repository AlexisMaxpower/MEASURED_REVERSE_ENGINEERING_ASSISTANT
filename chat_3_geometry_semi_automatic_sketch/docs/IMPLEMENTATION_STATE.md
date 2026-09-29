# Chat 3 — Implementation State

**Date:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Active branch:** `chat-3/pass-4`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Ring:** 4  
**Authorization:** explicit user-requested Pass 4; no Chat 6 `OD-004` was present on `main` when this branch was created.

## Baseline

Ring 4 was branched from the frozen Ring 3 head:

```text
08e716161a8c9173b7583d6ad87c84c10ddc4221
```

This preserves the complete Ring 3 OpenCV image-extraction implementation even though Chat 6 had not yet merged/published a Pass 4 directive on `main`.

## Capabilities implemented through Ring 3

- canonical CapturePackage / MeasurementPackage adapter;
- `IMAGE_PX -> MAT_XY_MM` homography normalization;
- POINT / LINE / CIRCLE / ARC geometry models;
- deterministic GeometryGraph;
- measurement binding;
- verified-vs-derived conflict visibility;
- deterministic SketchPackage v1 generation;
- OpenCV-backed reference-image LINE/CIRCLE/ARC candidate extraction;
- truthful `VISION_DETECTED` provenance;
- fail-closed ambiguous/unsupported geometry handling;
- stable image and golden fixtures.

## Ring 4 — Constraint Resolution

Ring 4 adds the previously missing promotion layer between internal constraint candidates and canonical `SketchPackage.constraints`.

New core component:

```text
ConstraintResolver
```

New data structures:

- `ResolvedConstraint`;
- `ConstraintIssue`;
- `ConstraintResolution`.

## Constraint promotion pipeline

```text
GeometryPipeline
        ↓
ConstraintCandidateEngine
        ↓
ConstraintResolver
        ↓
ResolvedConstraint + ConstraintIssue
        ↓
SketchPackageBuilder
        ↓
canonical constraints + unresolved
```

The resolver does not move entities and does not modify verified dimensions.

## Promotion policy

A relation is publishable only when:

1. every referenced entity exists;
2. effective confidence is at least the configured threshold;
3. it is not redundant with stronger already-observed axis relations;
4. it does not contradict verified physical measurements.

Default promotion confidence:

```text
0.95
```

Effective confidence:

```text
min(candidate confidence, confidence of referenced entities when present)
```

This prevents low-confidence vision geometry from becoming a high-confidence inferred CAD relation.

## Measurement truth guardrails

Main invariant remains:

```text
verified physical measurement > image-derived / geometry-derived relation
```

### EQUAL

If verified comparable intrinsic measurements disagree beyond tolerance, EQUAL is not published.

Code:

```text
VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT
```

### CONCENTRIC

If a verified center-distance for the entity pair is non-zero beyond tolerance, CONCENTRIC is not published.

Code:

```text
VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT
```

### Weak relation

If effective confidence is below promotion threshold:

```text
CONSTRAINT_BELOW_PROMOTION_CONFIDENCE
```

The relation stays explicit in `unresolved` rather than disappearing silently.

## Redundancy / overconstraint control

For axis-aligned lines:

- HORIZONTAL / VERTICAL are publishable;
- PARALLEL between two already-HORIZONTAL or two already-VERTICAL lines is omitted;
- PERPENDICULAR between already-HORIZONTAL and VERTICAL lines is omitted.

For rotated geometry, non-redundant PARALLEL / PERPENDICULAR candidates remain publishable.

## Builder compatibility

`SketchPackageBuilder.build()` accepts optional `constraint_resolution`.

If omitted:

```text
constraints = []
```

Therefore legacy/canonical Ring 1 fixture behavior remains unchanged.

Constraint-aware callers explicitly supply the resolution.

## Vision integration

Package-level `VisionGeometryPipeline` now composes:

```text
image extraction
→ GeometryPipeline
→ ConstraintResolver
→ SketchPackageBuilder
→ canonical unresolved merge
```

The Ring 3 image detector itself remains unchanged.

For the current vision fixture:

Published constraints:

- EQUAL opposite horizontal sides;
- EQUAL opposite vertical sides;
- HORIZONTAL bottom/top;
- VERTICAL left/right.

Not published:

- EQUAL between the two detected holes, because both CIRCLE entities have confidence `0.766`.

That relation is explicitly unresolved with `CONSTRAINT_BELOW_PROMOTION_CONFIDENCE`.

Verified dimensions remain exactly:

- width `40.0 mm`;
- height `20.0 mm`;
- hole diameter `8.0 mm`;
- center distance `20.0 mm`.

## Runtime version / dependencies

Package version:

```text
0.4.0
```

New Ring 4 dependencies: **none**.

Existing Ring 3 dependency retained:

```text
opencv-python-headless >=4.10,<5
```

## Verification

Authoritative GitHub Actions implementation-head run:

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
- `Integration / Chat 3 -> Chat 4`: **FAIL only because shared integration test still reads stale `cad_verification_report["dimensions"]` instead of canonical `cad_verification_report["items"]`**.

The Chat 3 -> Chat 4 test reaches successful CAD transfer and schema-valid CADVerificationReport before that stale lookup fails.

## Shared ownership

Ring 4 modifies no files under:

- `/core/contracts/`;
- `/tests/fixtures/contracts/`;
- `/tests/integration/`;
- `.github/`;
- Chat 1/2/4/5/6 directories.

No Change Request was required.

## Deferred Chat 3 work

- full constraint solving / geometry movement;
- COINCIDENT/TANGENT/SYMMETRIC candidate-generation policy;
- Dimensioned View renderer;
- multi-view geometry/constraints;
- CAD-native integration/read-back.

The next natural Chat 3 slice is Dimensioned View, unless Chat 6 issues a different directive.

## Current status

```text
READY_FOR_RING4_INTEGRATOR_REVIEW_WITH_PREEXISTING_CHAT3_TO_CHAT4_GATE_DEFECT
```

Chat 3 itself, canonical contracts, and Chat 2 -> Chat 3 are independently green on GitHub Actions.

## Ring 4 documents

- `BUILD_REUSE_CHECK_RING4_CONSTRAINT_RESOLUTION.md`;
- `IMPLEMENTATION_REPORT_RING4_CONSTRAINT_RESOLUTION_2026-09-29.md`;
- `ORCHESTRATOR_HANDOFF.md`.
