# Chat 1 — Implementation State

**Date:** 2026-09-29  
**Role:** Chat 1 — Project & Guided Capture  
**Current pass:** 3  
**Directive:** `OD-2026-09-29-003`  
**Working branch:** `chat-1/pass-3`  
**Baseline main SHA:** `c3452d7fa68c9c5c3716db5fef71172e9c3b9532`

## Source-of-truth order

1. current repository state for the active pass branch;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT + Chat 6 orchestration state/directive;
5. Chat 1 local docs.

Chat 1 does not modify shared contracts, canonical fixtures or Chat-6-owned CI/integration tests.

## Accepted baseline

### Pass 1 — accepted

- Project/Capture domain;
- manual capture baseline;
- canonical Project/Capture adapters;
- ChArUco calibration baseline.

### Pass 2 — accepted/integrated

- stable calibration provenance;
- deterministic perspective normalization;
- immutable rectified artifact;
- source/calibration/mat provenance;
- canonical CapturePackage backward compatibility.

## Pass 3 — Guided Capture Quality baseline

### Domain/result model

Added:

- `CaptureQualityVerdict`: `ACCEPT`, `WARN`, `REJECT`;
- `QualitySeverity`;
- `QualityReasonCode`;
- `CaptureQualityMetrics`;
- `CaptureQualityFinding`;
- `CaptureQualityResult`.

`CaptureSession.quality_analyses` persists one current-baseline analysis per immutable source frame and validates source-frame/view consistency.

### Analyzer

`OpenCvCaptureQualityAnalyzer` produces deterministic image diagnostics:

- `laplacian_variance` — focus/blur proxy;
- `mean_luma`;
- dark clipping fraction;
- bright clipping fraction;
- localized glare/highlight proxy fraction;
- edge density;
- border-edge ratio;
- optional ChArUco corner visibility ratio.

### Policy / verdict

`CaptureQualityPolicy` version:

`chat1.capture-quality.v1`

Rules are explicit and machine-readable. Each finding stores reason code, severity, observed metric, threshold and comparison operator.

Verdict aggregation:

```text
any REJECT finding -> REJECT
else any finding    -> WARN
else                -> ACCEPT
```

### Orchestration

`CaptureQualityService`:

- reads immutable clean-reference bytes through `ArtifactStore`;
- reuses existing calibration evidence when present;
- persists analysis result in CaptureSession;
- keeps source bytes unchanged;
- is idempotent for the same source/calibration/mat context;
- rejects conflicting reanalysis context rather than silently replacing provenance.

`RussianQualityGuidanceAdapter` converts reason codes into actionable Russian capture instructions without embedding presentation text into the quality policy itself.

## Ownership/truth boundary

Quality metrics are diagnostic proxies only.

They do **not**:

- create PhysicalMeasurement;
- alter verified measurement values;
- infer geometry;
- claim dimensional accuracy;
- alter canonical `CapturePackage v1`.

`CanonicalContractBuilder` ignores `quality_analyses`, preserving the accepted Chat 1 -> Chat 2 wire boundary.

## Local verification

New quality suite:

```text
8 passed in 0.21s
```

Verified generated cases:

- good sharp/balanced/centered image -> `ACCEPT`;
- strong blur -> `REJECT` / `BLUR`;
- severe underexposure -> `REJECT` / `UNDEREXPOSED`;
- severe overexposure -> `REJECT` / `OVEREXPOSED`;
- localized bright highlights -> `WARN` / `GLARE_RISK`;
- significant border activity -> `WARN` / `FRAMING_BORDER_ACTIVITY`;
- low ChArUco corner visibility -> `REJECT` / `LOW_MARKER_VISIBILITY`;
- repeated analysis produces equal deterministic result;
- persisted quality result does not change canonical CapturePackage;
- invalid image bytes fail explicitly.

A local all-tests run from the archive-restored workspace reached 21 passing tests and 3 failures solely because repository-root `core/contracts/mrea_contracts_v1.schema.json` is not present in that archive workspace. Those three tests fail at schema file loading, not Chat 1 behavior. Full branch CI is required as the authoritative complete regression.

## Current limitations

- policy thresholds are not yet calibrated on a real phone-camera dataset;
- blur metric is scene/resolution dependent;
- glare is a proxy, not physical specular modeling;
- framing is edge-based, not object segmentation;
- no lens-distortion-aware quality normalization;
- no native/mobile runtime validation;
- one persisted quality result per source frame/context in this baseline;
- quality verdict does not automatically mutate `CaptureViewStatus`.

## Pass 3 acceptance readiness

Before handoff freeze, require:

- Chat 1 branch tests green in GitHub Actions;
- `Integration / Chat 1 -> Chat 2` green;
- shared contract checks green;
- no shared-contract changes;
- final `ORCHESTRATOR_HANDOFF.md` published once, then branch frozen.


## Isolated Pass 4 work package — Guided Capture Readiness

While Round 3 final merge remains blocked by Chat-6-owned post-merge golden-path CI coverage, Chat 1 future work is isolated on `chat-1/pass-4` and is **not yet accepted/integrated**.

Added `guidance.py` with versioned deterministic readiness orchestration over existing capture evidence. It derives the first remaining required view and next action across clean reference, calibration, quality, measurement frame and explicit acceptance. Quality `REJECT` blocks progression; WARN handling is policy-controlled. Optional views do not block required completion.

This layer is pure/read-only and does not change `CapturePackage v1`, physical measurements, geometry, or persisted evidence.

Local schema-independent regression: `24 passed`. Full repository CI is required after upload.


## Isolated Pass 4 extension — immutable recapture / supersession lineage

The readiness flow previously had a dead-end after `QUALITY_REJECTED`: evidence was immutable, while the session allowed only one clean reference per view. The isolated branch now resolves that gap without deleting history.

Added lineage fields:

- `CaptureViewProgress.active_clean_reference_frame_id`;
- `FrameRecord.supersedes_frame_id` for clean-reference recapture chains;
- `FrameRecord.source_clean_reference_frame_id` for measurement-frame provenance.

Added `CaptureSessionService.recapture_clean_reference(...)`. It creates a new content-addressed clean artifact, links it to the previous active clean frame, updates only the active pointer, and preserves all previous evidence.

Calibration, rectification, quality, guided readiness and canonical serialization now resolve the active clean attempt by exact `source_frame_id`. Historical evidence remains persisted but is excluded from the active canonical package.

Backward compatibility:

- legacy sessions with one clean reference per view backfill `active_clean_reference_frame_id`;
- legacy measurement frames backfill their clean-reference provenance when it is unambiguous;
- existing canonical contracts remain unchanged.

Guided `QUALITY_REJECTED` / strict-WARN handling now returns the executable `RECAPTURE_CLEAN_REFERENCE` action.

Local schema-independent regression after this extension: `28 passed`. The remaining three full-suite failures in the patch workspace are only missing root-schema file loads; calibration/rectification/canonical behavior reaches those final validation calls successfully.

## Isolated Pass 4 work package — Explicit accepted-view revision

Added an explicit reopen/revision gate on top of immutable recapture lineage.

- `CaptureViewRevisionEvent` persists why/when an accepted view was reopened and which clean frame was active at that moment.
- `CaptureViewProgress.recapture_required` prevents silently reusing the previously accepted attempt.
- `CaptureSessionService.reopen_view(...)` only accepts `ACCEPTED` views, clears completion and records audit provenance.
- `accept_view(...)` fails while a fresh clean reference is still required.
- `recapture_clean_reference(...)` clears the gate only after a new immutable clean artifact is active.
- Guided Capture returns `RECAPTURE_CLEAN_REFERENCE` / `VIEW_REOPENED_RECAPTURE_REQUIRED` until recapture occurs.

Local schema-independent regression including quality: `33 passed in 0.32s`.
