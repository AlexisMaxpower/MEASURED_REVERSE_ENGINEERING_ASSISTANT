# ORCHESTRATOR HANDOFF — Chat 1

**Pass:** 2  
**Directive:** `OD-2026-09-29-002`  
**Branch:** `chat-1/pass-2`  
**Implementation final SHA:** `3c23710498bce52502f39456e641a99e2441d937`  
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

- added stable internal `calibration_id` to `CalibrationResult`;
- legacy calibration records without `calibration_id` receive deterministic UUIDv5 backfill from `source_frame_id + mat_id`;
- added `RectifiedReferenceRecord`;
- `CaptureSession` persists `rectified_references`;
- duplicate rectified reference per view is rejected.

## Rectification implementation

Added:

- `PerspectiveNormalizer` protocol;
- `OpenCvPerspectiveNormalizer`;
- `RectificationService`;
- `RectificationError`;
- `RectifiedRaster`.

Behavior:

- reuses existing stored calibration/homography;
- validates `MAT_XY_MM` coordinate system and matching mat profile;
- rejects singular or non-finite homography explicitly;
- derives deterministic raster size from mat dimensions + `pixels_per_mm`;
- fixed OpenCV interpolation, border and PNG encoding policy;
- original clean reference is never overwritten;
- rectified bytes are stored as a new content-addressed artifact;
- provenance links derived artifact to exact source frame, calibration ID and mat ID.

## Canonical contract compatibility

Canonical `CapturePackage v1` has no rectified-artifact property and its view objects reject unknown properties.

Therefore Pass 2 does not modify `core/contracts` or canonical fixtures. The rectified artifact remains internal to Chat 1. The canonical package continues to expose the original clean-reference artifact and calibration homography.

The Pass 2 regression proves canonical serialization is unchanged before/after internal rectification and remains schema-valid.

## Exact tests executed

Local full Chat 1 regression:

```text
pytest -q
................                                                         [100%]
16 passed in 1.17s
```

New Pass 2 coverage verifies:

1. synthetic 5x7 ChArUco reference warped with known perspective geometry;
2. existing calibration recovers the source-to-mat homography;
3. repeated normalization produces identical encoded PNG bytes;
4. original clean-reference bytes remain retrievable and unchanged;
5. derived artifact has separate artifact ID and SHA-256;
6. provenance contains exact `source_frame_id`, `calibration_id`, and `mat_id`;
7. output is 1000x1400 at 10 px/mm for the 100x140 mm mat;
8. rectified image matches known canonical geometry with mean absolute pixel error `< 8`;
9. canonical CapturePackage before/after rectification is unchanged and schema-valid;
10. singular homography fails explicitly;
11. legacy calibration without `calibration_id` receives stable deterministic identity.

## Acceptance target status

OD-002 requires:

- deterministic synthetic perspective rectification — **satisfied**;
- preserved original artifact — **satisfied**;
- explicit source/calibration provenance — **satisfied**;
- canonical CapturePackage backward compatibility/schema validity — **satisfied**;
- no fabricated scalar calibration quality — **satisfied** (`quality` remains `null`).

## Limitations

- real printed Measurement Mat accuracy is not verified;
- camera lens distortion/intrinsics are not compensated;
- deterministic encoded bytes are tied to the fixed current OpenCV/runtime baseline, not promised across arbitrary future OpenCV versions;
- rectified artifact is internal because canonical v1 has no exposure field;
- replacement/versioning for a rectified reference is not implemented;
- mobile/native runtime and GitHub Actions CI are not verified.

## Files changed in Pass 2

- `src/mrea_capture/models.py`;
- `src/mrea_capture/rectification.py`;
- `src/mrea_capture/__init__.py`;
- `tests/test_rectification.py`;
- `docs/BUILD_REUSE_CHECK_PHASE3_RECTIFICATION.md`;
- `docs/IMPLEMENTATION_REPORT_PASS2_RECTIFICATION_2026-09-29.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `README.md`;
- `ORCHESTRATOR_HANDOFF.md`.

## Acceptance requested from Chat 6

Please verify:

1. `OD-2026-09-29-002` acceptance gate is satisfied;
2. internal rectified-artifact exposure policy is acceptable for canonical v1;
3. Pass 2 may be accepted as the new Chat 1 baseline;
4. update Orchestration State / Slice Status as appropriate;
5. issue the next directive before Pass 3.
