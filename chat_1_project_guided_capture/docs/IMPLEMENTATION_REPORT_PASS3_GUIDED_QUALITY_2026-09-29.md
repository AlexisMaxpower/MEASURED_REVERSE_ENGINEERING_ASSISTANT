# IMPLEMENTATION REPORT — Chat 1 / Pass 3 Guided Capture Quality Baseline

**Directive:** `OD-2026-09-29-003`  
**Branch:** `chat-1/pass-3`  
**Date:** 2026-09-29

## Delivered

Implemented the first deterministic guided-capture quality layer for clean reference images.

```text
immutable clean reference
+ optional calibration evidence
+ optional MeasurementMatProfile
→ OpenCV diagnostic metrics
→ machine-readable findings
→ ACCEPT / WARN / REJECT
→ persisted internal quality result
→ optional Russian actionable guidance
```

## Models

Added internal models/enums:

- `CaptureQualityVerdict`;
- `QualitySeverity`;
- `QualityReasonCode`;
- `CaptureQualityMetrics`;
- `CaptureQualityFinding`;
- `CaptureQualityResult`.

`CaptureSession` now persists `quality_analyses` and validates that each result references a real frame in the same view. Current baseline allows one persisted quality analysis per immutable source frame.

## Quality implementation

Added `quality.py` with:

- `CaptureQualityPolicy`;
- `CaptureQualityAnalyzer` protocol;
- `OpenCvCaptureQualityAnalyzer`;
- `CaptureQualityService`;
- `CaptureQualityError`;
- `RussianQualityGuidanceAdapter`.

### Signals

1. **Blur/focus proxy** — variance of Laplacian.
2. **Exposure** — mean luma plus dark/bright clipping fractions.
3. **Glare proxy** — small/medium connected high-value, low-saturation regions.
4. **Scene/framing proxy** — edge density and border-edge ratio.
5. **Marker visibility** — existing ChArUco corner count divided by the expected corner count of the supplied Measurement Mat profile.

All metrics remain diagnostic image evidence. None is emitted as physical dimensional truth.

## Verdict semantics

Policy rules emit deterministic findings with:

- reason code;
- severity (`WARN` / `REJECT`);
- metric name;
- observed value;
- threshold;
- comparison operator.

Verdict aggregation is deterministic:

- any `REJECT` finding → `REJECT`;
- otherwise any finding → `WARN`;
- no findings → `ACCEPT`.

## Provenance

Each `CaptureQualityResult` records:

- deterministic `analysis_id`;
- source clean-reference `frame_id`;
- view;
- calibration ID when calibration is used;
- mat ID when available;
- quality policy version.

The analyzer ID is deterministic for the same source frame + policy + calibration/mat context.

## Canonical compatibility

No shared contract or canonical fixture is modified.

Quality analysis is internal to Chat 1. `CanonicalContractBuilder` ignores `quality_analyses`, therefore adding/persisting a quality result does not change `CapturePackage v1` serialization.

This preserves the accepted Chat 1 → Chat 2 canonical boundary.

## Local verification

New Pass 3 quality suite:

```text
pytest -q tests/test_quality.py
........                                                                 [100%]
8 passed in 0.21s
```

Generated deterministic fixtures verify:

- sharp balanced centered frame → `ACCEPT`;
- strong Gaussian blur → `REJECT` / `BLUR`;
- severe underexposure → `REJECT` / `UNDEREXPOSED`;
- severe overexposure → `REJECT` / `OVEREXPOSED`;
- localized bright highlight patches → `WARN` / `GLARE_RISK`;
- full-frame structure reaching borders → `WARN` / `FRAMING_BORDER_ACTIVITY`;
- low ChArUco corner visibility → `REJECT` / `LOW_MARKER_VISIBILITY`;
- repeated analysis of identical immutable input is deterministic;
- service persistence is idempotent for the same frame/context;
- source image bytes remain unchanged;
- canonical CapturePackage is unchanged before/after quality analysis;
- invalid image bytes fail explicitly.

The local archive workspace does not contain repository-root `core/contracts`, so three existing contract-validation tests cannot complete there; they reach schema-load and fail only on missing local root schema. Full repository CI on the branch is the authoritative complete regression gate and must be checked before handoff freeze.

## Files changed

- `src/mrea_capture/models.py`;
- `src/mrea_capture/quality.py`;
- `src/mrea_capture/__init__.py`;
- `tests/test_quality.py`;
- `docs/BUILD_REUSE_CHECK_PASS3_GUIDED_QUALITY.md`;
- this report;
- `docs/IMPLEMENTATION_STATE.md`;
- `README.md`;
- final `ORCHESTRATOR_HANDOFF.md` at branch freeze.

## Known limitations

- thresholds are software-policy defaults, not yet calibrated on real phone-camera datasets;
- Laplacian variance depends on scene content/resolution;
- glare detection is a proxy, not photometric/specular modeling;
- framing is edge-based and does not segment the physical part;
- no lens-distortion-aware quality normalization yet;
- no native/mobile runtime validation yet;
- current persisted baseline supports one quality result per immutable source frame/context;
- quality verdict does not automatically overwrite or alter existing `CaptureViewStatus` transitions.

## Acceptance target status

Implementation satisfies the OD-003 software requirements locally. Final acceptance requires branch CI to keep green:

- Chat 1 / Capture;
- Integration / Chat 1 -> Chat 2;
- shared contract checks.
