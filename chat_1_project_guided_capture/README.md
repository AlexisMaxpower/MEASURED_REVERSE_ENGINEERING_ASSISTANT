# Chat 1 — Project & Guided Capture

Chat 1 owns the MREA vertical slice from Project/Capture setup through canonical `CapturePackage` production and guided-capture preprocessing. Shared contracts remain owned by Chat 6.

## Current orchestration

- Pass 1: **accepted** by Chat 6;
- Pass 2: **accepted** and integrated into `main`;
- current directive: `OD-2026-09-29-003`;
- Pass 3 branch: `chat-1/pass-3`;
- Pass 3 gate: Guided Capture Quality baseline.

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

### Calibration and rectification

- `MeasurementMatProfile`;
- `CalibrationResult` with stable internal `calibration_id`;
- OpenCV ChArUco detection;
- RANSAC homography `IMAGE_PX -> MAT_XY_MM`;
- calibration provenance tied to clean reference;
- deterministic perspective normalization;
- immutable rectified artifact + source/calibration provenance;
- canonical CapturePackage remains backward compatible.

### Pass 3 — Guided Capture Quality

- `CaptureQualityPolicy` with versioned thresholds;
- `OpenCvCaptureQualityAnalyzer`;
- blur/focus proxy (Laplacian variance);
- mean-luma + clipping exposure diagnostics;
- glare/highlight proxy;
- edge-density + border-edge framing diagnostics;
- optional reuse of ChArUco corner visibility;
- machine-readable `QualityReasonCode` findings;
- explicit `ACCEPT` / `WARN` / `REJECT` verdict;
- persisted source/calibration/mat provenance;
- Russian actionable guidance adapter;
- quality analysis remains internal and does not alter metric truth or canonical contracts.

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
│  ├─ quality.py
│  ├─ guidance.py
│  ├─ rectification.py
│  ├─ repositories.py
│  └─ services.py
├─ tests/
│  ├─ test_project_service.py
│  ├─ test_capture_plan.py
│  ├─ test_manual_capture.py
│  ├─ test_canonical_contracts.py
│  ├─ test_calibration.py
│  ├─ test_rectification.py
│  ├─ test_quality.py
│  └─ test_guidance.py
└─ docs/
   ├─ IMPLEMENTATION_STATE.md
   ├─ BUILD_REUSE_CHECK_PASS3_GUIDED_QUALITY.md
   └─ IMPLEMENTATION_REPORT_PASS3_GUIDED_QUALITY_2026-09-29.md
```

## Pass 3 local verification

```text
pytest -q tests/test_quality.py
........                                                                 [100%]
8 passed in 0.21s
```

The generated fixtures cover good capture, strong blur, under/over exposure, localized glare, border-framing risk, low marker visibility, deterministic repeated analysis, persistence and explicit decode failure.

Full repository CI is required for final Pass 3 acceptance because the local archive workspace does not contain repository-root shared-contract files.

## Contract policy

Guided quality is internal diagnostic state. `CapturePackage v1` is unchanged; no quality inference is emitted as physical measurement truth.

## Remaining work after Pass 3

Subject to the next Chat 6 directive:

- real-device threshold calibration;
- printed Measurement Mat / physical accuracy validation;
- camera lens/intrinsics strategy;
- richer framing/object guidance if a safe segmentation boundary is approved;
- native/mobile camera integration;
- voice-trigger capture in its later roadmap gate.


## Isolated Pass 4 — Guided Capture Readiness

Pending Round-3 closure / official OD-004, `chat-1/pass-4` contains an isolated future-work layer that derives deterministic next actions and required-view completeness from existing CaptureSession evidence. It does not modify canonical contracts and must not be treated as integrated into `main` until orchestration approval.
