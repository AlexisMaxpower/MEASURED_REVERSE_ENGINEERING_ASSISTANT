# ORCHESTRATOR HANDOFF — Chat 1

**Pass:** 3  
**Directive:** `OD-2026-09-29-003`  
**Branch:** `chat-1/pass-3`  
**Baseline main SHA:** `c3452d7fa68c9c5c3716db5fef71172e9c3b9532`  
**Implementation / pre-handoff SHA:** `13241df21ed501e6697d773e5c672be0e3c8359e`  
**Final branch SHA:** the branch HEAD containing this handoff; this commit freezes the branch  
**Date:** 2026-09-29  
**From:** Chat 1 — Project & Guided Capture  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Contract baseline:** `mrea.contracts.v1`

## Delivered

Pass 3 implements the first deterministic Guided Capture Quality baseline required by OD-003:

```text
immutable clean reference
+ optional calibration evidence
+ optional MeasurementMatProfile
→ deterministic OpenCV diagnostic metrics
→ machine-readable quality findings
→ ACCEPT / WARN / REJECT
→ persisted internal quality analysis
→ optional Russian actionable guidance
```

## Ownership and contract boundary

No shared contract, canonical fixture, Chat-6-owned CI file or integration test was modified.

Quality analysis remains internal to Chat 1 and is explicitly diagnostic. It does not:

- create or alter `PhysicalMeasurement`;
- claim metric/dimensional truth;
- infer sketch/CAD geometry;
- overwrite clean-reference evidence;
- add fields to `CapturePackage v1`.

`CanonicalContractBuilder` continues to ignore internal quality state, preserving the accepted Chat 1 → Chat 2 boundary.

## Domain/result model

Added:

- `CaptureQualityVerdict`: `ACCEPT`, `WARN`, `REJECT`;
- `QualitySeverity`;
- `QualityReasonCode`;
- `CaptureQualityMetrics`;
- `CaptureQualityFinding`;
- `CaptureQualityResult`.

`CaptureSession` now persists `quality_analyses` and validates:

- one current-baseline result per immutable source frame;
- source frame exists in the session;
- result view matches source frame view.

## Analyzer and policy

Added `quality.py` with:

- `CaptureQualityPolicy` (`chat1.capture-quality.v1`);
- `CaptureQualityAnalyzer` protocol;
- `OpenCvCaptureQualityAnalyzer`;
- `CaptureQualityService`;
- `CaptureQualityError`;
- `RussianQualityGuidanceAdapter`.

Signals:

1. blur/focus proxy — variance of Laplacian;
2. mean luma;
3. dark clipping fraction;
4. bright clipping fraction;
5. localized glare/highlight proxy;
6. edge density / low-scene-detail proxy;
7. border-edge ratio / framing proxy;
8. optional ChArUco corner visibility from existing calibration evidence.

Framing deliberately does not perform object segmentation. Glare deliberately remains a conservative image proxy rather than photometric/specular truth.

## Verdict behavior

Every finding contains:

- machine-readable reason code;
- severity (`WARN` / `REJECT`);
- metric name;
- observed value;
- threshold;
- comparison operator.

Aggregation is deterministic:

```text
any REJECT finding -> REJECT
else any finding    -> WARN
else                -> ACCEPT
```

Russian guidance is produced by a presentation adapter from reason codes; user-facing text is not hidden inside the decision logic.

## Provenance / persistence

Each result records:

- deterministic `analysis_id`;
- immutable source `frame_id`;
- view;
- calibration ID when used;
- mat ID when available;
- policy version.

`CaptureQualityService` reads source bytes through `ArtifactStore`, preserves them unchanged and is idempotent for the same source/calibration/mat context. A conflicting reanalysis context is explicit rather than silently replacing provenance.

## Deterministic fixture coverage

New tests cover:

- sharp/balanced/centered image → `ACCEPT`;
- strong Gaussian blur → `REJECT` / `BLUR`;
- severe underexposure → `REJECT` / `UNDEREXPOSED`;
- severe overexposure → `REJECT` / `OVEREXPOSED`;
- localized highlights → `WARN` / `GLARE_RISK`;
- full-frame border activity → `WARN` / `FRAMING_BORDER_ACTIVITY`;
- low ChArUco corner visibility → `REJECT` / `LOW_MARKER_VISIBILITY`;
- deterministic repeated analysis;
- service persistence and idempotency;
- immutable original source bytes;
- unchanged canonical CapturePackage before/after quality analysis;
- explicit decode failure for invalid bytes.

## Local tests executed

Focused Pass 3 quality suite:

```text
pytest -q tests/test_quality.py
........                                                                 [100%]
8 passed
```

Quality + baseline capture subset:

```text
pytest -q tests/test_quality.py tests/test_project_service.py tests/test_capture_plan.py tests/test_manual_capture.py
..................                                                       [100%]
18 passed
```

The archive-restored local workspace lacks repository-root `core/contracts`, so three pre-existing schema-loading tests cannot complete there. This limitation is environmental to that local workspace; full branch CI below ran against the complete repository and is authoritative.

## GitHub Actions evidence before handoff freeze

Workflow: `MREA CI`  
Run ID: `36619586794`  
Run number: `107`  
Head SHA: `13241df21ed501e6697d773e5c672be0e3c8359e`

Required Pass 3 gates:

- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 1 / Capture` — **SUCCESS**;
- `Integration / Chat 1 -> Chat 2` — **SUCCESS**.

Other executable slice jobs on the same run also completed successfully. Integration gates unrelated to the Chat 1 branch were conditionally skipped as intended by CI policy.

Per Pass 3 process, this handoff is the final branch mutation. Chat 6 owns independent post-handoff/PR CI evidence and acceptance review.

## Files changed in Pass 3

- `src/mrea_capture/models.py`;
- `src/mrea_capture/quality.py`;
- `src/mrea_capture/__init__.py`;
- `tests/test_quality.py`;
- `docs/BUILD_REUSE_CHECK_PASS3_GUIDED_QUALITY.md`;
- `docs/IMPLEMENTATION_REPORT_PASS3_GUIDED_QUALITY_2026-09-29.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `README.md`;
- `ORCHESTRATOR_HANDOFF.md` (this final freeze commit).

## Known limitations

- policy thresholds are deterministic software defaults, not yet calibrated on a real phone-camera dataset;
- Laplacian blur score depends on scene content and resolution;
- glare detection is a proxy, not photometric/specular modeling;
- framing is edge-based, not object segmentation;
- no lens-distortion-aware quality normalization yet;
- no native/mobile runtime validation yet;
- current persisted baseline keeps one quality result per immutable source frame/context;
- quality verdict does not automatically mutate existing `CaptureViewStatus` transitions.

## Open Change Requests

None.

## Acceptance requested from Chat 6

Please verify:

1. `OD-2026-09-29-003` Guided Capture Quality requirements are satisfied;
2. ownership/truth boundaries remain intact;
3. `CapturePackage v1` compatibility and Chat 1 → Chat 2 gate remain accepted;
4. branch/PR CI remains green after the frozen handoff commit;
5. if accepted, integrate Pass 3 and issue the next Chat 1 directive.

**Branch freeze:** no further Chat 1 commits will be pushed to `chat-1/pass-3` unless Chat 6 explicitly returns `FIX_REQUIRED`.
