# Chat 1 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 1 — Project & Guided Capture  
**Orchestrator directive:** `OD-2026-09-29-001`

## Source of truth

1. current `main`;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT + orchestration state/directives;
5. Chat 1 docs.

Chat 1 does not modify shared contracts.

## Implemented

### R1 Phase 1 — Project/Capture domain

- Project/Part context;
- stable `project_id` + `part_id`;
- legacy stable `part_id` backfill;
- deterministic CapturePlan;
- local Project persistence/services.

### R1 Phase 2 — Manual Capture

- CaptureSession persistence;
- CameraMetadata;
- separate clean-reference / measurement frames;
- content-addressed artifact storage + SHA-256;
- required-view completion rules;
- evidence frame ordering invariants.

### Orchestrator canonical gate

- `ProjectContract v1` adapter;
- `CapturePackage v1` builder;
- canonical ArtifactReference and MeasurementCaptureFrame mapping;
- deterministic opaque package/view IDs;
- schema tests against Integrator-owned v1 schema;
- `OD-2026-09-29-001` FRONT schema-valid acceptance target satisfied.

### R1 Phase 3 — Calibration baseline

- `MeasurementMatProfile`;
- `CalibrationResult` persisted in CaptureSession;
- `CalibrationDetector` abstraction;
- `OpenCvCharucoCalibrationDetector`;
- ChArUco marker/corner detection;
- RANSAC homography `IMAGE_PX -> MAT_XY_MM`;
- detected marker/corner evidence;
- reprojection RMSE in mm;
- calibration provenance tied to clean reference frame;
- canonical non-null `CapturePackage.views[].calibration`;
- synthetic ChArUco integration test.

`calibration.quality` intentionally remains `null`: no approved scalar quality formula exists yet.

## Verification

Latest full local Chat 1 regression:

```text
13 passed in 1.07s
```

Verified synthetic calibration result:

- 5x7 ChArUco board;
- 24 detected ChArUco corners;
- marker detection succeeds;
- 9-value homography produced;
- reprojection RMSE `< 0.001 mm` on synthetic fixture;
- canonical CapturePackage with calibration validates against shared schema.

Environment used for verification:

- Python 3.12+ compatible code;
- Pydantic 2.13.4;
- pytest 9.0.2;
- jsonschema 4.26.0;
- OpenCV 4.13.0 with ArUco/ChArUco;
- NumPy 2.x.

No GitHub Actions CI has been run.

## Current Build/Reuse decision

OpenCV ArUco/ChArUco is reused for fiducial detection and homography. MREA owns mat identity/configuration, provenance, persistence, canonical mapping and acceptance policy. OpenCV code is isolated behind `CalibrationDetector`.

## Not implemented yet

### Remaining R1 Phase 3

- perspective-normalized derived image artifact;
- explicit source -> rectified artifact relation;
- deterministic warp test with synthetic perspective distortion;
- physical printed Measurement Mat verification;
- lens distortion/intrinsics strategy.

### R1 Phase 4 — Guided Quality

- blur/focus;
- exposure;
- glare/shadow;
- tilt;
- framing;
- perspective warning;
- background quality;
- feature occlusion;
- actionable guidance.

### Later

- native/mobile camera adapter;
- voice-trigger capture;
- API;
- CI.

## Known limitations

- current detector uses planar homography and does not compensate camera lens distortion;
- real-world metric accuracy is not yet established;
- duplicate calibration of one view is explicit error, not silent replacement;
- artifact URI resolver is not globally implemented yet;
- image MIME is not decoded against declared MIME outside calibration path;
- concurrent JSON writers are unsupported.

## Immediate next step

Implement perspective normalization using stored homography:

1. define rectified-frame internal model;
2. derive image in deterministic `MAT_XY_MM` raster space;
3. store rectified image as a new immutable artifact;
4. preserve clean-reference -> rectified provenance;
5. test against synthetically perspective-distorted ChArUco input;
6. expose rectified artifact to later Geometry without replacing the original evidence frame.

## Integration readiness

Ready for Chat 6 review:

- Project/Capture domain;
- canonical Project/Capture boundary;
- schema-valid FRONT CapturePackage;
- ChArUco calibration baseline in canonical package;
- 13 passing tests.

Not ready:

- physical calibration validation;
- rectified derived image artifact;
- guided quality;
- native camera/mobile integration;
- CI.
