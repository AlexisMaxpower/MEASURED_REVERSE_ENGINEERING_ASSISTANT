# ORCHESTRATOR HANDOFF — Chat 1

**Product Pass:** 2  
**Coordination Pass:** 3 — CI / acceptance closure  
**Directive:** `OD-2026-09-29-002`  
**Branch:** `chat-1/pass-2`  
**Review PR:** `#16`  
**Implementation final SHA:** `3c23710498bce52502f39456e641a99e2441d937`  
**Green CI evidence head:** `b1cabe7627bba984319ac40c942b1d13b424cce9`  
**Green CI run:** `36610773229` / run `#28`  
**Date:** 2026-09-29  
**From:** Chat 1 — Project & Guided Capture  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Contract baseline:** `mrea.contracts.v1`

## Delivered

Pass 2 implements the perspective-normalization gate required by OD-002:

```text
immutable clean reference
+ stored IMAGE_PX -> MAT_XY_MM homography
+ MeasurementMatProfile
-> deterministic rectified raster
-> immutable derived artifact
-> explicit source/calibration provenance
```

## Branch policy

All Pass 2 implementation was written to:

`chat-1/pass-2`

No Pass 2 implementation was committed directly to `main`.

## Domain changes

- stable internal `calibration_id` in `CalibrationResult`;
- deterministic UUIDv5 backfill for legacy calibration records;
- `RectifiedReferenceRecord`;
- persisted `CaptureSession.rectified_references`;
- duplicate rectified reference per view rejected.

## Rectification implementation

Added:

- `PerspectiveNormalizer` protocol;
- `OpenCvPerspectiveNormalizer`;
- `RectificationService`;
- `RectificationError`;
- `RectifiedRaster`.

Behavior:

- reuses existing stored calibration/homography;
- validates `MAT_XY_MM` and matching mat profile;
- rejects singular/non-finite homography explicitly;
- derives raster size from mat dimensions + `pixels_per_mm`;
- fixed OpenCV interpolation/border/PNG encoding policy;
- original clean reference is never overwritten;
- rectified bytes are a new content-addressed artifact;
- provenance links exact source frame, calibration ID and mat ID.

## Canonical compatibility

No shared schema or canonical fixture was modified.

`CapturePackage v1` has no rectified-artifact field and rejects unknown view properties. The rectified artifact therefore remains internal to Chat 1. Canonical output continues to expose original clean reference + calibration homography.

Regression coverage proves canonical serialization before/after internal rectification remains unchanged and schema-valid.

## Exact local tests executed

```text
pytest -q
................                                                         [100%]
16 passed in 1.13s
```

Coverage verifies:

1. non-identity synthetic perspective distortion;
2. existing calibration recovers source-to-mat homography;
3. deterministic repeated PNG bytes;
4. preserved original clean-reference bytes;
5. separate derived artifact identity/SHA-256;
6. exact `source_frame_id`, `calibration_id`, `mat_id` provenance;
7. 1000x1400 raster at 10 px/mm for 100x140 mm mat;
8. mean absolute pixel error `< 8` against canonical geometry;
9. canonical CapturePackage unchanged and schema-valid;
10. singular homography explicit failure;
11. stable legacy calibration-ID migration.

## GitHub Actions evidence

PR `#16` has a successful MREA CI run:

- workflow run ID: `36610773229`;
- run number: `28`;
- conclusion: `success`;
- checked PR/branch head: `b1cabe7627bba984319ac40c942b1d13b424cce9`.

Passed jobs:

- Contracts / canonical fixtures;
- Chat 1 / Capture;
- Chat 2 / Measurement;
- Chat 3 / Geometry;
- Chat 4 / Generic CAD gate;
- Chat 5 / Lifecycle;
- Integration / Chat 2 -> Chat 3.

Expected conditional skip:

- Integration / Chat 4 -> Chat 5 — skipped because this is not a Chat 5 PR.

Earlier failed runs on intermediate branch states are superseded by successful run `36610773229`.

This handoff/state documentation update is documentation-only. The branch push triggers CI again; Chat 6 should use the newest PR #16 run as the final acceptance evidence if a newer run exists.

## OD-002 acceptance target

- deterministic synthetic perspective rectification — **SATISFIED**;
- preserved original artifact — **SATISFIED**;
- explicit source/calibration provenance — **SATISFIED**;
- canonical backward compatibility/schema validity — **SATISFIED**;
- no fabricated scalar calibration quality — **SATISFIED**;
- executable GitHub CI evidence — **SATISFIED**.

## Files changed by product Pass 2

- `src/mrea_capture/models.py`;
- `src/mrea_capture/rectification.py`;
- `src/mrea_capture/__init__.py`;
- `tests/test_rectification.py`;
- `docs/BUILD_REUSE_CHECK_PHASE3_RECTIFICATION.md`;
- `docs/IMPLEMENTATION_REPORT_PASS2_RECTIFICATION_2026-09-29.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `README.md`;
- `ORCHESTRATOR_HANDOFF.md`.

Coordination Pass 3 adds no product functionality; it only records independent CI evidence and closes the handoff gap.

## Tests not executed / environment gaps

- real printed Measurement Mat accuracy;
- phone camera lens-distortion/intrinsics validation;
- native/mobile runtime;
- physical mm accuracy against external metrology.

## Known limitations

- deterministic encoded bytes are tied to the pinned current OpenCV/runtime behavior;
- rectified artifact is internal because canonical v1 has no exposure field;
- no rectified-reference replacement/versioning policy;
- no Guided Quality implementation yet.

## Open Change Requests

None.

## Acceptance requested from Chat 6

Please verify and close `OD-2026-09-29-002` for Chat 1, integrate PR `#16` if the newest required CI is green, update orchestration state, and issue the next directive before new product work begins.
