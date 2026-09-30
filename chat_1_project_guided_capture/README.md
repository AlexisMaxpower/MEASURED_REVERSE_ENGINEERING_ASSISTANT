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
│  ├─ lineage.py
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
│  ├─ test_guidance.py
│  ├─ test_recapture.py
│  └─ test_reopen.py
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


### Isolated Pass 4 extension — immutable recapture lineage

The guided workflow can now recover from a rejected clean-reference attempt without deleting evidence:

- each view stores an explicit `active_clean_reference_frame_id`;
- a recaptured clean frame records `supersedes_frame_id`;
- measurement frames record `source_clean_reference_frame_id`;
- prior clean/calibration/quality/rectification/measurement evidence remains immutable;
- calibration, quality, rectification, readiness and canonical serialization resolve only the active attempt;
- canonical `CapturePackage v1` exposes only active clean-reference evidence and active-attempt measurement frames;
- accepted views cannot be silently recaptured without a future explicit reopen workflow.

This remains isolated on `chat-1/pass-4` until Round 3 closes and Chat 6 issues the official next directive.

### Isolated Pass 4 — Explicit accepted-view revision

Accepted views can now be intentionally reopened through an audited `reopen_view(...)` operation. Reopening never deletes evidence: it records a `CaptureViewRevisionEvent`, clears completion, and requires a fresh clean-reference attempt before the view can be accepted again. Guided Capture exposes this as `RECAPTURE_CLEAN_REFERENCE` with `VIEW_REOPENED_RECAPTURE_REQUIRED`. This state remains internal and does not change `CapturePackage v1`.

### Isolated Pass 4 extension — deterministic capture-attempt history

`history.py` now projects the immutable clean-reference lineage into an explicit per-view attempt history for UI/orchestration. Each attempt carries its clean artifact identity, predecessor/successor links, acceptance/revision evidence, calibration, quality verdict, rectification and measurement-frame IDs. The projection is read-only and keeps active vs historical evidence unambiguous. The history projection fails closed on multiple roots, disconnected clean-reference components, missing predecessors, branches or cycles.

