# ORCHESTRATOR HANDOFF — Chat 3 — Pass 3

**From:** Chat 3 — Geometry & Semi-Automatic Sketch  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Directive:** `OD-2026-09-29-003`  
**Pass / Ring:** 3  
**Branch:** `chat-3/pass-3`  
**Branch base:** `c3452d7fa68c9c5c3716db5fef71172e9c3b9532`  
**Implementation head before handoff commit:** `8bc9ed6aa6e68db61b1d201cd3667d8f8658fc9a`  
**Date:** 2026-09-29

> This handoff is the final worker commit for Pass 3. After it is published, Chat 3 treats `chat-3/pass-3` as frozen until Chat 6 returns an explicit integration verdict or new directive.

## Status

`READY_FOR_RING3_INTEGRATOR_REVIEW_WITH_ORCHESTRATOR_GATE_DEFECT`

## Delivered functionality

Ring 3 implements the first real image-backed semi-automatic geometry candidate path.

### Image extraction

Added OpenCV-backed `ImageGeometryExtractor` using established CV operations for:

- grayscale image decoding;
- Otsu thresholding;
- contour hierarchy;
- polygon approximation;
- contour area/perimeter/circularity;
- connected components;
- minimum enclosing circle.

### v1 geometry candidates

Reliable observations may produce:

- `LINE` candidates from a dominant quadrilateral profile;
- `CIRCLE` candidates from circular inner contours;
- controlled `ARC` candidates from open circular components.

All image-derived geometry uses:

```text
provenance = VISION_DETECTED
```

No CV candidate is promoted to measured/user-confirmed truth.

### Measurement truth

Verified canonical measurements remain authoritative. Ring 3 image extraction supplies entity candidates only; it does not rewrite:

- `measurement_id`;
- value;
- unit;
- verified status;
- measurement provenance.

### Fail-closed ambiguity behavior

Unsupported/ambiguous observations are explicit rather than guessed. Examples include:

- no usable reference contour;
- multiple significant outer contours;
- unsupported non-quadrilateral outer shape;
- non-circular inner contour;
- unreliable open circular fit/coverage;
- CIRCLE/ARC under calibration that does not preserve circles.

These issues can be projected into canonical `SketchPackage.unresolved`.

### Calibration semantics

LINE geometry may be transformed through a valid projective homography.

CIRCLE/ARC promotion is restricted to circle-preserving similarity transforms. A general projective homography maps a circle to a conic, so Chat 3 does not silently fabricate a circle/arc in `MAT_XY_MM`.

## Runtime dependency

Added:

```text
opencv-python-headless >=4.10,<5
```

No GUI dependency was introduced.

## Stable fixtures / golden coverage

Added textual PBM evidence and goldens under:

`chat_3_geometry_semi_automatic_sketch/tests/fixtures/vision/`

including:

- calibrated front reference image;
- verified MeasurementPackage;
- exact image → SketchPackage golden;
- controlled open-arc image;
- exact ARC geometry golden.

## Files changed / added in Pass 3

Runtime / package:

- `pyproject.toml`;
- `src/mrea_geometry/__init__.py`;
- `src/mrea_geometry/vision.py`.

Tests / fixtures:

- `tests/test_vision_extraction.py`;
- `tests/fixtures/vision/front_plate_reference.pbm`;
- `tests/fixtures/vision/front_plate_sketch_golden.json`;
- `tests/fixtures/vision/open_arc_reference.pbm`;
- `tests/fixtures/vision/open_arc_geometry_golden.json`;
- `tests/fixtures/vision/vision_capture_package.json`;
- `tests/fixtures/vision/vision_measurement_package.json`.

Documentation / handoff:

- `docs/BUILD_REUSE_CHECK_RING3_VISION_EXTRACTION.md`;
- `docs/IMPLEMENTATION_REPORT_RING3_VISION_EXTRACTION_2026-09-29.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md`.

Total final Pass 3 changed paths: **14**.

## Verification

### Local reconstructed regression

```text
20 passed, 4 deselected in 1.03s
```

The deselected checks require repository-level shared contract paths absent from the reconstructed local workspace; they are covered by GitHub-hosted CI.

### GitHub Actions implementation-head evidence

Workflow run:

```text
36620011768
```

Implementation head:

```text
299a9c5b4531bf0c4a04bd3a2b452eea6e70d84e
```

Results:

- `Chat 3 / Geometry`: **SUCCESS — 28 passed in 0.31s**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- `Chat 2 / Measurement`: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: **SUCCESS**;
- `Chat 4 / Generic CAD gate`: **SUCCESS**;
- `Integration / Chat 3 -> Chat 4`: **FAIL due orchestrator-owned integration-test defect described below**.

## External integration-gate defect

The Chat 3 → Chat 4 test successfully:

1. builds the Chat 3 `SketchPackage`;
2. validates it against canonical schema;
3. runs Chat 4 CAD transfer;
4. validates `CADPackage`;
5. validates `CADVerificationReport`;
6. confirms `overall_status == VERIFIED`.

It then fails inside the shared integration test with:

```text
KeyError: 'dimensions'
```

because the test accesses:

```python
transfer.cad_verification_report["dimensions"]
```

while canonical `CADVerificationReport v1` exposes the verification array as:

```python
transfer.cad_verification_report["items"]
```

The stale integration test currently exists on `main` with blob SHA:

```text
3057d91f79ee19a86e1245d4366de7209269c557
```

Per OD-003 ownership rules, Chat 3 did **not** modify `tests/integration/` or weaken the gate.

## Requested Chat 6 action

Correct or explicitly reclassify the orchestrator-owned Chat 3 → Chat 4 integration gate:

```text
cad_verification_report["dimensions"]
→
cad_verification_report["items"]
```

Then rerun repository CI against `chat-3/pass-3` before final integration acceptance.

## Shared ownership / Change Requests

Shared contracts changed: **none**.  
Shared canonical fixtures changed: **none**.  
Shared integration tests changed: **none**.  
Other chat directories changed: **none**.  
Open Change Requests: **none**.

## Known limitations

- outer-profile LINE promotion is intentionally conservative;
- CIRCLE/ARC are not invented from a non-circle-preserving projective transform;
- ellipse/conic vocabulary is not added to v1;
- no hidden-edge inference;
- no general constraint solver;
- no Dimensioned View renderer;
- no multi-view reconstruction;
- no CAD logic inside Chat 3.

## Integrator review target

Review/fix the external shared gate, then validate:

```text
reference image
+ calibrated CapturePackage
+ verified MeasurementPackage
→ VISION_DETECTED LINE/CIRCLE/ARC candidates
→ measurement binding without measurement mutation
→ deterministic schema-valid SketchPackage v1
→ Chat 4 canonical consumption
```

Branch is frozen after this handoff commit pending Chat 6 verdict.
