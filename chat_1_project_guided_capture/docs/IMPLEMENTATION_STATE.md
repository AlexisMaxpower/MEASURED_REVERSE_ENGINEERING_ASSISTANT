# Chat 1 — Implementation State

**Date:** 2026-09-29  
**Role:** Chat 1 — Project & Guided Capture  
**Current pass:** 2  
**Directive:** `OD-2026-09-29-002`  
**Working branch:** `chat-1/pass-2`

## Source-of-truth order

1. current repository state for the active pass branch;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT + Chat 6 orchestration state/directive;
5. Chat 1 local docs.

Chat 1 does not modify shared contracts or canonical fixtures.

## Accepted baseline — Pass 1

Chat 6 accepted:

- Project/Capture domain;
- manual capture baseline;
- stable project/part linkage;
- canonical `ProjectContract v1` / `CapturePackage v1` adapters;
- ChArUco calibration baseline;
- schema-valid FRONT CapturePackage with calibration.

## Pass 2 implemented

### Stable calibration provenance

- `CalibrationResult.calibration_id` added as an internal identifier;
- legacy calibration records without the field receive deterministic UUIDv5 backfill from source frame + mat identity.

### Perspective normalization

Added:

- `RectifiedReferenceRecord`;
- `CaptureSession.rectified_references` persistence;
- `PerspectiveNormalizer` protocol;
- `OpenCvPerspectiveNormalizer`;
- `RectificationService`;
- explicit `RectificationError` failures.

Flow:

```text
clean reference artifact
+ stored calibration homography
+ MeasurementMatProfile
+ pixels_per_mm
-> deterministic MAT-space raster
-> new content-addressed artifact
-> RectifiedReferenceRecord
```

Invariants:

- source clean artifact is never overwritten;
- derived artifact has independent artifact ID/SHA;
- source frame ID is preserved in provenance;
- exact calibration ID and mat ID are preserved;
- one rectified reference per view in current baseline;
- singular/non-finite homographies fail explicitly;
- existing calibration is reused; no second calibration representation exists.

### Canonical boundary

No shared contract change.

`CapturePackage v1` has no rectified-artifact property. Rectification therefore stays internal while the canonical package continues to expose original clean reference + calibration homography. Canonical serialization before and after internal rectification remains unchanged.

## Verification

Latest full local Chat 1 regression:

```text
16 passed in 1.17s
```

Pass 2 synthetic perspective test verifies:

- known perspective distortion of a 5x7 ChArUco board;
- calibration of the distorted reference;
- deterministic repeated encoded output;
- preserved source bytes;
- distinct derived artifact identity/hash;
- source/calibration/mat provenance;
- 1000x1400 raster at 10 px/mm for 100x140 mm mat geometry;
- mean absolute image error `< 8` against known canonical raster;
- canonical CapturePackage remains schema-valid and unchanged;
- singular homography explicit failure;
- stable legacy calibration-ID backfill.

## Current limitations

- no real printed-mat accuracy validation;
- no camera lens-distortion/intrinsics compensation;
- deterministic raster policy is pinned to current OpenCV behavior, not promised across arbitrary future versions;
- rectified artifact is internal until/if Chat 6 creates a canonical exposure path;
- no rectified-reference replacement/versioning policy;
- no Guided Quality implementation yet;
- native/mobile runtime and CI are not verified.

## Integration readiness

Ready for Chat 6 Pass 2 acceptance review:

- deterministic perspective normalization;
- immutable derived artifact;
- explicit source/calibration provenance;
- source evidence preservation;
- canonical backward compatibility;
- full local regression passing.

Next work must follow the next Chat 6 directive after Pass 2 acceptance.
