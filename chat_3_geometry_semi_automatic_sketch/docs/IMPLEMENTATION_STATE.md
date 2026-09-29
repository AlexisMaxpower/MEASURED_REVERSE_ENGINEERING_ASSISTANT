# Chat 3 — Implementation State

**Date:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Active branch:** `chat-3/pass-3`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Directive:** `OD-2026-09-29-003`  
**Ring:** 3

## Accepted baseline

Ring 2 was accepted and merged by Chat 6. The real Chat 2 `IMAGE_PX` → Chat 3 `MAT_XY_MM` boundary is green and remains unchanged.

Existing accepted capabilities include:

- canonical CapturePackage / MeasurementPackage normalization;
- calibrated homography application;
- POINT / LINE / CIRCLE / ARC geometry models;
- GeometryGraph;
- measurement binding;
- verified-vs-derived conflict visibility;
- deterministic SketchPackage v1 generation;
- canonical unresolved projection.

## Ring 3 implemented

### Real image candidate extraction

Added `ImageGeometryExtractor` backed by `opencv-python-headless`.

Reliable v1 promotion currently covers:

- quadrilateral outer profiles → deterministic LINE candidates;
- circular inner features → CIRCLE candidates;
- controlled open circular components → ARC candidates.

All promoted image geometry uses:

```text
provenance = VISION_DETECTED
```

and confidence below 1.0.

### Measurement truth

Image geometry is candidate evidence only. Existing verified dimensions remain sourced from canonical measurements and are never rewritten by CV.

The tested reference flow is:

```text
reference image + CapturePackage calibration
        ↓
ImageGeometryExtractor
        ↓
VISION_DETECTED primitives
        +
verified MeasurementPackage
        ↓
GeometryPipeline
        ↓
VisionGeometryPipeline / SketchPackageBuilder
        ↓
deterministic SketchPackage v1
```

### Fail-closed behavior

Unsupported or ambiguous observations remain explicit instead of becoming guessed geometry.

Examples:

- ambiguous significant outer contours;
- unsupported outer contour shape;
- non-circular inner contour;
- non-circle-preserving projective transform for CIRCLE/ARC;
- unreliable open-curve fit or coverage.

Candidate issues are projected into canonical `SketchPackage.unresolved`.

### Calibration semantics

LINE points may use a valid projective homography.

CIRCLE/ARC promotion requires a circle-preserving similarity transform because a general projective homography maps a circle to a conic. Chat 3 does not silently collapse such a conic back into a circle.

## Stable fixtures / golden tests

Added textual PBM reference images and deterministic golden outputs under:

`tests/fixtures/vision/`

Coverage includes:

- front plate image with outer rectangle and two holes;
- exact image → SketchPackage golden;
- open circular arc image;
- exact ARC golden;
- calibrated CapturePackage;
- verified MeasurementPackage.

## Verification

Local reconstructed workspace regression run:

```text
20 passed, 4 deselected in 1.03s
```

The four deselected tests require repository-level shared contract files absent from the reconstructed local workspace.

GitHub Actions implementation-head run:

```text
run: 36620011768
head: 299a9c5b4531bf0c4a04bd3a2b452eea6e70d84e
```

Results relevant to Chat 3:

- `Chat 3 / Geometry`: **SUCCESS — 28 passed in 0.31s**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: **SUCCESS**;
- `Chat 4 / Generic CAD gate`: **SUCCESS**;
- `Integration / Chat 3 -> Chat 4`: **FAIL due orchestrator-owned test defect, not Ring 3 output**.

The failing integration test reads:

```text
cad_verification_report["dimensions"]
```

but canonical `CADVerificationReport v1` and Chat 4 expose verification entries as:

```text
cad_verification_report["items"]
```

The same stale integration-test access remains on current `main`. Chat 3 does not modify `tests/integration/` per OD-003 ownership rules.

## Shared ownership

Ring 3 changes no files under:

- `/core/contracts/`;
- `/tests/fixtures/contracts/`;
- `/tests/integration/`;
- Chat 1/2/4/5/6 directories.

## Not implemented / intentionally deferred

- arbitrary free-form contour reconstruction;
- ellipse/conic vocabulary outside v1;
- hidden-edge inference;
- general constraint solver;
- dimensioned-view renderer;
- multi-view reconstruction;
- CAD logic.

## Current status

`READY_FOR_RING3_INTEGRATOR_REVIEW_WITH_ORCHESTRATOR_GATE_DEFECT`

Chat 3 code and its upstream boundary are green. Chat 6 must correct or reclassify the stale Chat 3→4 integration test before declaring the repository-wide Pass 3 gate green.

## Ring 3 docs

- `BUILD_REUSE_CHECK_RING3_VISION_EXTRACTION.md`;
- `IMPLEMENTATION_REPORT_RING3_VISION_EXTRACTION_2026-09-29.md`;
- `ORCHESTRATOR_HANDOFF.md`.
