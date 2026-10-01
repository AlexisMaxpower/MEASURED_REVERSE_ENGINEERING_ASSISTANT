# Chat 1 — Pass 4 Guided Capture Readiness Implementation Report

**Date:** 2026-09-30  
**Branch target:** `chat-1/pass-4`  
**Round status:** isolated future-work package; Round 3 final merge is still blocked by Chat-6-owned post-merge golden-CI coverage.

## Implemented

Added `src/mrea_capture/guidance.py`.

### Models / policy

- `GuidedCaptureAction`
- `GuidedCaptureBlockerCode`
- `GuidedCapturePolicy`
- `GuidedViewReadiness`
- `GuidedCaptureReadiness`
- `GuidedCaptureError`

Default policy version:

`chat1.guided-capture.v1`

### Service

`GuidedCaptureReadinessService.evaluate(session)` derives, without mutating state:

- readiness for every planned view;
- evidence IDs already present for that view;
- quality verdict if available;
- machine-readable blockers;
- deterministic next action;
- first remaining required view in capture-plan order;
- required workflow completion.

Default action progression:

```text
CAPTURE_CLEAN_REFERENCE
  -> RUN_CALIBRATION
  -> ANALYZE_QUALITY
  -> [RESOLVE_QUALITY if rejected]
  -> CAPTURE_MEASUREMENT_FRAME
  -> ACCEPT_VIEW
  -> COMPLETE
```

### Quality policy interaction

- `REJECT` always blocks progression;
- `WARN` proceeds by default;
- `GuidedCapturePolicy(allow_quality_warn=False)` converts WARN into explicit `RESOLVE_QUALITY`.

### Optional views

Optional views remain visible in per-view guidance but do not appear in `required_views_remaining` and do not prevent top-level `COMPLETE` after all required views are accepted.

## Tests

Added `tests/test_guidance.py` covering:

1. full deterministic action progression;
2. rejected-quality blocking;
3. explicit WARN policy behavior;
4. optional-view non-blocking completion;
5. deterministic/no-mutation evaluation;
6. canonical `CapturePackage` unchanged by guidance evaluation.

Local verification excluding tests that require the repository-root canonical schema:

```text
24 passed in 0.24s
```

A broader local run reached 25 passing tests plus two failures caused only by the archive-restored workspace missing `core/contracts/mrea_contracts_v1.schema.json`; both failures occur at schema file loading in existing calibration/rectification tests. Repository CI remains the authoritative full regression once the branch is pushed.

## Contract / ownership impact

None.

- no `core/contracts` changes;
- no shared integration-test changes;
- no Chat 2–5 changes;
- no new metric truth;
- canonical CapturePackage remains unchanged.

## Current orchestration caveat

At implementation time `main` still publishes `OD-2026-09-29-003` and Chat 8 has blocked Round-3 final merge on shared CI post-merge golden-path coverage. This Pass-4 work is therefore intentionally isolated and must not be represented as accepted/integrated until Chat 6/7/8 close Round 3 and issue the next Chat 1 directive.
