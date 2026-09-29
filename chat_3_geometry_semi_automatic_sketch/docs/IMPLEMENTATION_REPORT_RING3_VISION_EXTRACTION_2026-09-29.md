# Chat 3 — Ring 3 Implementation Report — Vision Geometry Extraction

**Date:** 2026-09-29  
**Directive:** `OD-2026-09-29-003`  
**Branch:** `chat-3/pass-3`

## Objective

Replace the deterministic primitive-only fixture boundary with the first real semi-automatic reference-image → geometry candidate slice while preserving the metrology invariant:

```text
verified physical measurement > image-derived geometry
```

## Delivered

### OpenCV extraction boundary

New module:

`src/mrea_geometry/vision.py`

Public API:

- `ImageGeometryExtractor`;
- `GeometryExtractionResult`;
- `CandidateIssue`;
- `VisionGeometryPipeline`.

The extractor uses OpenCV for image decoding, thresholding, contour hierarchy, polygon approximation, connected components and circle fitting.

### LINE

A reliable dominant quadrilateral profile is promoted to deterministic LINE candidates. For the calibrated FRONT fixture the candidates are:

- `L-BOTTOM`;
- `L-RIGHT`;
- `L-TOP`;
- `L-LEFT`.

### CIRCLE

Circular child contours are promoted to deterministic CIRCLE candidates only when the calibration transform preserves circles.

The front fixture yields two ordered holes:

- `C-HOLE-1` / `HOLE_1`;
- `C-HOLE-2` / `HOLE_2`.

### ARC

A controlled open connected component is fit as a circular ARC only when radial residual and angular coverage pass explicit reliability bounds and calibration preserves circles.

### Provenance

Every promoted image primitive is emitted as:

```text
VISION_DETECTED
```

No image primitive is marked as measured or user-confirmed.

### Unresolved handling

Ambiguous or unsupported observations become `CandidateIssue` and are projected to canonical `SketchPackage.unresolved`.

No scale, hidden edge, conic-to-circle conversion, or unsupported contour is guessed silently.

## Measurement binding

The image-derived primitives feed the already accepted `GeometryPipeline`.

Canonical verified measurements retain their exact:

- `measurement_id`;
- value;
- unit;
- verified flag;
- measurement provenance.

The image geometry supplies entity candidates only.

## Stable fixtures

Added under `tests/fixtures/vision/`:

- `front_plate_reference.pbm`;
- `open_arc_reference.pbm`;
- `vision_capture_package.json`;
- `vision_measurement_package.json`;
- `front_plate_sketch_golden.json`;
- `open_arc_geometry_golden.json`.

PBM is deliberately textual so exact image evidence is repository-reviewable and Git-blob-verifiable.

## Tests added

`tests/test_vision_extraction.py` verifies:

1. exact reference-image → canonical SketchPackage golden;
2. schema-valid SketchPackage;
3. truthful `VISION_DETECTED` provenance;
4. verified measurement values remain unchanged;
5. repeated extraction is deterministic;
6. projective LINE transform remains allowed while CIRCLE invention is rejected;
7. unsupported profile remains explicit unresolved;
8. candidate issue projects into canonical unresolved;
9. controlled ARC image matches exact geometry golden.

## Runtime dependency

`pyproject.toml` version moved to `0.3.0` and adds:

```text
opencv-python-headless >=4.10,<5
```

No GUI dependency is required.

## Verification

### Local reconstructed regression

```text
20 passed, 4 deselected in 1.03s
```

Deselected tests require repository-level canonical files absent from the reconstructed local workspace.

### GitHub Actions

Implementation head:

```text
299a9c5b4531bf0c4a04bd3a2b452eea6e70d84e
```

Run:

```text
36620011768
```

Observed results:

- Chat 3 / Geometry — **SUCCESS, 28 passed in 0.31s**;
- Contracts / canonical fixtures — **SUCCESS**;
- Chat 2 / Measurement — **SUCCESS**;
- Integration / Chat 2 -> Chat 3 — **SUCCESS**;
- Chat 4 / Generic CAD gate — **SUCCESS**;
- Integration / Chat 3 -> Chat 4 — **FAIL: stale orchestrator-owned field name in integration test**.

## External integration blocker

The Chat 3→4 test successfully creates and schema-validates both `CADPackage` and `CADVerificationReport`, then fails only when the test itself reads:

```python
transfer.cad_verification_report["dimensions"]
```

Canonical `CADVerificationReport v1` defines the verification array as `items`, and Chat 4 emits `items`.

Therefore this failure is not repaired inside Chat 3. `OD-003` explicitly forbids Chat 3 from changing shared integration tests. The same stale lookup is present on current `main`.

Requested Chat 6 action:

```text
correct/reclassify tests/integration/test_chat3_to_chat4_boundary.py
"dimensions" -> canonical "items"
```

then re-run the repository gate against this branch.

## Shared files changed

None.

## Change Requests

None. The existing v1 vocabulary is sufficient for this slice.

## Known limitations

- outer-profile promotion is intentionally conservative and currently targets reliable quadrilateral LINE geometry;
- CIRCLE/ARC are rejected under non-circle-preserving projective calibration;
- ellipse/conic vocabulary is not introduced;
- no hidden geometry inference;
- no multi-view reconstruction;
- no CAD logic in Chat 3.

## Result

Ring 3 implements the first real image-backed semi-automatic sketch candidate path. Chat 3 unit behavior and the real Chat 2→3 boundary are green. Repository-wide acceptance awaits the orchestrator-owned Chat 3→4 integration-test correction.
