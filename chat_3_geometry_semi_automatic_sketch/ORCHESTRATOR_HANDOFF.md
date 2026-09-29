# ORCHESTRATOR HANDOFF — Chat 3 — Pass 5

**From:** Chat 3 — Geometry & Semi-Automatic Sketch  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Pass / Ring:** 5  
**Branch:** `chat-3/pass-5`  
**Branch base:** frozen Ring 4 head `aa53603b4f845b63a0962ddacd921ea4dbf01b54`  
**Implementation/docs head before handoff commit:** `7c292ac20698ffd53a020c510fa902942ab89387`  
**Date:** 2026-09-30

## Authorization / baseline note

Ring 5 was started by explicit user instruction. At start, `main` still exposed Chat 3 directive `OD-2026-09-29-003`; no newer Chat 3 worker directive had been published.

To preserve the complete user-authorized Ring 4 work, `chat-3/pass-5` was created from the frozen Ring 4 head rather than from current `main`.

No shared contracts, shared CI, shared integration tests, or other chat-owned files were modified.

## Status

`READY_FOR_RING5_INTEGRATOR_REVIEW`

## Delivered functionality

Ring 5 implements the first deterministic **Dimensioned View** slice required by the product SSOT:

```text
Clean Reference Image
+
Geometry Overlay
+
Dimension Lines
+
Physical Measurements
+
Confidence / Provenance
```

### New runtime module

`src/mrea_geometry/dimensioned_view.py`

Public API:

- `ReferenceImageLayer`;
- `DimensionedViewArtifact`;
- `DimensionedViewRenderer`.

### Deterministic SVG output

The renderer accepts canonical `SketchPackage v1` in `MAT_XY_MM` and emits deterministic SVG.

Supported v1 geometry visuals:

- `POINT`;
- `LINE`;
- `CIRCLE`;
- `ARC`.

Supported canonical dimension visuals:

- `DISTANCE`;
- `DIAMETER`;
- `RADIUS`;
- `ANGLE`.

### Measurement/provenance traceability

Dimension markup preserves/displays:

- `dimension_id`;
- `measurement_id` when present;
- canonical physical value and unit;
- provenance;
- verified state.

Geometry markup preserves/displays:

- `entity_id`;
- provenance;
- confidence when available.

The footer exposes geometry provenance/confidence, dimension provenance and canonical unresolved items.

### Truth hierarchy

The renderer is read-only.

It never:

- recalculates or replaces a verified measurement value;
- changes unit or verification state;
- upgrades provenance;
- resolves a conflict;
- moves geometry;
- infers hidden geometry.

The invariant remains:

```text
verified physical measurement > image-derived / geometry-derived information
```

### Clean reference image

A clean reference image may be composed under the overlay only through `ReferenceImageLayer` with explicit `MAT_XY_MM` bounds.

Ring 5 does **not** guess image registration from pixel dimensions or sketch extents. Invalid/non-positive image bounds fail closed.

### Slice-local artifact

`DimensionedViewArtifact` is intentionally local to Chat 3.

It is not a new shared wire contract and does not replace the canonical downstream boundary:

```text
SketchPackage v1 -> Chat 4
```

## Golden / tests

New exact golden:

`tests/fixtures/dimensioned_view/front_plate_dimensioned_view.svg`

New acceptance suite:

`tests/test_dimensioned_view.py`

Coverage includes:

1. exact byte-for-byte SVG golden;
2. XML well-formedness;
3. measurement/provenance/verified traceability;
4. explicit reference-image bounds;
5. deterministic and read-only rendering;
6. POINT/LINE/CIRCLE/ARC visuals;
7. DISTANCE/DIAMETER/RADIUS/ANGLE visuals;
8. fail-closed invalid coordinate space and missing entity references.

## Runtime / dependencies

Package version:

```text
0.5.0
```

New Ring 5 dependencies: **none**.

Existing Ring 3 OpenCV dependency remains unchanged.

## GitHub Actions verification

Implementation head:

```text
9244a0f58e0fda35504ae5a7004cdaa0af40ef94
```

Workflow run:

```text
36637771870
```

Authoritative Chat 3 result:

```text
41 passed in 0.42s
```

Observed checks:

- `Chat 3 / Geometry`: **SUCCESS — 41 passed**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- Chat 1/2/4/5 slice jobs: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: test step **SUCCESS**;
- `Integration / Chat 3 -> Chat 4`: **FAIL only because this worker branch inherits the pre-fix shared test from its frozen Ring 4 base**.

## Chat 3 -> Chat 4 baseline drift

The worker branch inherited the old shared test lookup:

```python
cad_verification_report["dimensions"]
```

instead of canonical:

```python
cad_verification_report["items"]
```

The failing CI reaches successful SketchPackage generation, schema validation, Chat 4 transfer, CADPackage validation, CADVerificationReport validation and `overall_status == VERIFIED`, then fails at that stale field lookup.

Current `main` has already fixed this shared test in orchestrator commit:

```text
1a54ef40f84119d7482d971deb1e58749bf657b0
```

Do not interpret that worker-branch failure as a Ring 5 regression. Integrator should replay/merge the Ring 5 worker diff onto the current corrected shared baseline rather than backport shared infrastructure into Chat 3.

## Current shared Round 3 infrastructure note

Current `main` also contains Chat 8 finding `ROUND_3_FINAL_REVIEW_FINDING_001_CANDIDATE_CI.md`, which identifies incomplete CI execution for `integration/pass-3-candidate` as a Chat 6-owned shared CI issue.

The finding explicitly states this is not a worker-slice defect and worker branches should not be reopened to work around it.

Ring 5 changes no shared CI.

## Shared ownership / Change Requests

Shared contracts changed: **none**.  
Shared canonical fixtures changed: **none**.  
Shared integration tests changed: **none**.  
CI changed: **none**.  
Other chat directories changed: **none**.  
Change Requests: **none**.

## Integrator review target

Validate/replay onto current shared baseline:

```text
SketchPackage v1
→ deterministic DimensionedViewRenderer
→ geometry overlay
→ canonical physical dimensions
→ provenance/confidence traceability
→ explicit unresolved display
→ optional explicitly registered clean reference image
```

Verify that the derived visual artifact does not mutate the SketchPackage or physical truth.

## Known limitations / next owned work

Deferred unless Chat 6 changes priority:

- richer annotation collision/layout optimization;
- interactive evidence navigation from dimension labels;
- COINCIDENT/TANGENT/SYMMETRIC candidate-generation policy;
- numerical solver/entity movement;
- multi-view geometry/constraint relationships;
- CAD-native logic.

## Branch freeze

This handoff is the final normal worker commit for Ring 5.

After publication, `chat-3/pass-5` is treated as **frozen** pending Chat 6 verdict or explicit user/orchestrator instruction.

The only permitted post-handoff write is a minimal repair if the required final GitHub upload audit proves that a claimed Ring 5 file failed to land; any such repair must itself be re-audited.
