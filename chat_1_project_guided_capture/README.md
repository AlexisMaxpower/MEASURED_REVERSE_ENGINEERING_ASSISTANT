# Chat 1 — Project & Guided Capture

Chat 1 owns the MREA vertical slice from Project/Capture setup through canonical `CapturePackage` production and guided-capture preprocessing. Shared contracts remain owned by Chat 6.

## Current orchestration

- Pass 1: **accepted** by Chat 6.
- Current directive: `OD-2026-09-29-002`.
- Pass 2 branch: `chat-1/pass-2`.
- Pass 2 gate: perspective normalization / derived reference artifact.

## Current implementation

### Project / capture

- `Project` + `PartContext` with stable `project_id` / `part_id`;
- deterministic CapturePlan;
- persistent offline-first CaptureSession;
- clean-reference and measurement-frame separation;
- content-addressed local ArtifactStore with SHA-256 verification.

### Canonical boundary

- `ProjectContract v1` adapter;
- `CapturePackage v1` builder;
- ArtifactReference / MeasurementCaptureFrame mapping;
- schema-valid canonical FRONT flow;
- canonical ChArUco calibration in `MAT_XY_MM`.

### Calibration

- `MeasurementMatProfile`;
- `CalibrationResult` with stable internal `calibration_id`;
- OpenCV ChArUco detection;
- RANSAC homography `IMAGE_PX -> MAT_XY_MM`;
- calibration provenance tied to clean reference.

### Pass 2 — perspective normalization

- `PerspectiveNormalizer` abstraction;
- `OpenCvPerspectiveNormalizer`;
- deterministic MAT-space raster dimensions;
- explicit invalid/singular-homography failures;
- immutable rectified image artifact;
- `RectifiedReferenceRecord`;
- provenance: source clean frame + calibration + mat;
- original clean reference remains unchanged/retrievable;
- canonical CapturePackage remains backward-compatible and schema-valid.

## Structure

```text
chat_1_project_guided_capture/
├─ ORCHESTRATOR_DIRECTIVE.md
├─ ORCHESTRATOR_HANDOFF.md
├─ pyproject.toml
├─ src/mrea_capture/
│  ├─ artifacts.py
│  ├─ calibration.py
│  ├─ contracts.py
│  ├─ models.py
│  ├─ rectification.py
│  ├─ repositories.py
│  └─ services.py
├─ tests/
│  ├─ test_project_service.py
│  ├─ test_capture_plan.py
│  ├─ test_manual_capture.py
│  ├─ test_canonical_contracts.py
│  ├─ test_calibration.py
│  └─ test_rectification.py
└─ docs/
   ├─ IMPLEMENTATION_STATE.md
   ├─ BUILD_REUSE_CHECK_PHASE3_RECTIFICATION.md
   └─ IMPLEMENTATION_REPORT_PASS2_RECTIFICATION_2026-09-29.md
```

## Verification

Latest local full regression for Pass 2:

```text
16 passed in 1.17s
```

The synthetic perspective regression uses known geometry and verifies deterministic encoded output, source preservation, provenance, derived artifact separation, explicit singular-homography failure and canonical schema compatibility.

## Contract policy

`CapturePackage v1` currently has no field for a rectified artifact and disallows unknown view properties. Pass 2 therefore keeps the rectified artifact internal rather than silently extending the canonical wire contract.

## Remaining work

- physical printed-mat validation;
- camera lens/intrinsics strategy;
- Guided Quality warnings;
- native/mobile camera integration;
- voice-trigger capture (later roadmap gate);
- CI.
