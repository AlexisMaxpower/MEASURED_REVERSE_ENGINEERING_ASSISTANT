# Chat 3 — Ring 5 Implementation Report — Dimensioned View

**Date:** 2026-09-30  
**Ring:** 5  
**Branch:** `chat-3/pass-5`  
**Base:** frozen Ring 4 head `aa53603b4f845b63a0962ddacd921ea4dbf01b54`  
**Authorization:** explicit user-requested continuation. No newer Chat 6 worker directive for Chat 3 was present when Ring 5 started.

## Objective

Implement the Chat 3-owned **Dimensioned View** required by the product SSOT:

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

The view is a derived engineering visualization. It is not a new measurement source and it does not replace `SketchPackage v1` as the canonical Chat 3 -> Chat 4 boundary.

## Delivered

### Deterministic SVG renderer

New runtime module:

`src/mrea_geometry/dimensioned_view.py`

New public types:

- `ReferenceImageLayer`;
- `DimensionedViewArtifact`;
- `DimensionedViewRenderer`.

The renderer consumes a canonical `SketchPackage v1` in `MAT_XY_MM` and produces deterministic SVG.

### v1 entity visualization

Supported canonical entity types:

- `POINT`;
- `LINE`;
- `CIRCLE`;
- `ARC`.

Entity output retains traceability as SVG data/title metadata including:

- `entity_id`;
- provenance;
- confidence when available.

### Dimension visualization

Supported canonical dimension types:

- `DISTANCE`;
- `DIAMETER`;
- `RADIUS`;
- `ANGLE`.

Dimension markup preserves/displays:

- `dimension_id`;
- `measurement_id` when present;
- physical value and unit;
- provenance;
- verified/unverified state.

The renderer never recomputes the canonical dimension value from the drawing and never changes the verified state.

### Traceability footer

The generated SVG includes a deterministic footer containing:

- geometry provenance summary;
- geometry confidence range;
- dimension provenance summary;
- statement that verified state is preserved from SketchPackage;
- every canonical unresolved item by id/code.

Thus low-confidence or conflicting information does not disappear from the visual artifact.

### Optional Clean Reference Image

A clean image can be composed under the geometry overlay via `ReferenceImageLayer`.

Image registration is **never guessed** from image pixel dimensions or sketch extents.

The caller must supply explicit image bounds in `MAT_XY_MM`:

- `min_x_mm`;
- `min_y_mm`;
- `max_x_mm`;
- `max_y_mm`.

Invalid/non-positive bounds fail closed.

This preserves the SSOT requirement to support a Clean Reference Image while avoiding fabricated image-to-geometry alignment.

### Deterministic layout

Ring 5 provides deterministic:

- entity ordering;
- dimension ordering;
- projection from model millimetres to SVG coordinates;
- annotation lanes;
- extension/dimension lines and arrow markers;
- numeric formatting;
- SVG metadata/footer ordering.

Given identical input and renderer parameters, the SVG output is byte-for-byte stable.

## Truth / provenance rules

The renderer is read-only and preserves the existing MREA hierarchy:

```text
verified physical measurement > image/geometry inference
```

It does not:

- change `measurement_id`;
- change measured values or units;
- upgrade provenance;
- promote unresolved items;
- resolve geometry conflicts;
- move geometry;
- infer hidden features.

## Exact golden artifact

Added:

`tests/fixtures/dimensioned_view/front_plate_dimensioned_view.svg`

The golden is generated from the existing Ring 4 front-plate `SketchPackage` and therefore visibly contains:

- `VISION_DETECTED` outer geometry and two holes;
- line confidence `0.990`;
- hole confidence `0.766`;
- verified `MANUAL_MEASURED` dimensions `40 / 20 / 8 / 20 mm`;
- explicit unresolved low-confidence hole-equality constraint.

## Tests

Added `tests/test_dimensioned_view.py` covering:

1. exact byte-for-byte SVG golden;
2. XML well-formedness and traceability metadata;
3. explicit clean-image MAT bounds and no guessed alignment;
4. deterministic/read-only behavior;
5. all v1 entity and dimension visual types;
6. fail-closed invalid coordinate space / missing dimension entity references.

## Runtime / dependencies

Package version:

```text
0.5.0
```

New Ring 5 dependencies: **none**.

Existing Ring 3 dependency remains:

```text
opencv-python-headless >=4.10,<5
```

## Verification

### Local focused verification

```text
python -m compileall -q src tests
19 passed
```

The reconstructed local workspace does not contain repository-level `core/contracts/` and canonical fixtures, so the complete repository suite is verified through GitHub Actions rather than using those missing local paths as evidence.

### GitHub Actions

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

Observed shared checks:

- `Chat 3 / Geometry`: **SUCCESS — 41 passed**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- Chat 1/2/4/5 slice jobs: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: test step **SUCCESS**;
- `Integration / Chat 3 -> Chat 4`: **FAIL on stale shared integration test inherited from the Ring 4 base**.

## Chat 3 -> Chat 4 baseline drift

`chat-3/pass-5` intentionally branches from frozen Ring 4 head to preserve the user-authorized Ring 4 work. Therefore it also inherits the pre-fix shared integration test that reads:

```python
cad_verification_report["dimensions"]
```

instead of canonical:

```python
cad_verification_report["items"]
```

The Ring 5 CI reaches successful Chat 3 SketchPackage generation, canonical validation, Chat 4 transfer, CADPackage validation, CADVerificationReport validation and `overall_status == VERIFIED`, then fails only on that stale field lookup.

Current `main` has already corrected this shared test in orchestrator commit:

```text
1a54ef40f84119d7482d971deb1e58749bf657b0
```

Ring 5 does not backport or modify the Chat 6-owned shared integration test. Integrator should replay/merge Ring 5 worker changes onto the corrected current shared baseline.

## Current Round 3 orchestration note

Current `main` is simultaneously undergoing Round 3 candidate certification. Chat 8 identified a separate shared CI coverage issue for `integration/pass-3-candidate`. That finding explicitly states it is not a worker-slice defect and worker branches must not be reopened to work around it.

Ring 5 changes no shared CI.

## Shared ownership

Ring 5 changes no files under:

- `core/contracts/`;
- `tests/fixtures/contracts/`;
- `tests/integration/`;
- `.github/`;
- Chat 1/2/4/5/6/7/8 directories.

No Change Request was required because Dimensioned View is a slice-local derived artifact and does not alter `SketchPackage v1`.

## Deferred Chat 3 work

Still deferred unless Chat 6 reprioritizes:

- richer automatic annotation collision/layout optimization;
- interactive UI wiring for clicking a dimension and opening evidence;
- `COINCIDENT` / `TANGENT` / `SYMMETRIC` candidate-generation policy;
- numerical constraint solving/entity movement;
- multi-view geometry relationships;
- CAD-native logic.

## Result

Ring 5 closes the first deterministic Dimensioned View vertical slice while preserving measurement truth and provenance. The Chat 3 package is green on a real GitHub-hosted checkout with **41 tests passing**, and no shared contract or downstream CAD semantics were modified.
