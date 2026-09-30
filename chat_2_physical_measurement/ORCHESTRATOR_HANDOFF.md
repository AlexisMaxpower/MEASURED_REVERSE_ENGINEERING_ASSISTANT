# ORCHESTRATOR HANDOFF — Chat 2

**Pass:** 7  
**Branch:** `chat-2/pass-7`  
**Baseline:** frozen Pass-6 head `539d58567046fd29ccf2d42b629227ffe8da6546`  
**Executable implementation SHA:** `2f45383a685b22508df4b9aa5bf1ea3dbf1a2caf`  
**Implementation CI:** `MREA CI` run `36652682345` / run #410  
**Date:** 2026-09-30  
**From:** Chat 2 — Physical Measurement  
**To:** Chat 6 / integration review

> This handoff is the final worker commit for Pass 7. The branch is frozen after this file update. No post-handoff worker commit should be added unless integration review explicitly returns a fix request.

## Orchestration note

Pass 7 is stacked on frozen Pass 6 because at pass start:

- PR #31 (`chat-2/pass-6 -> chat-2/pass-5`) was still open;
- current `main` had advanced to Round 3 integration;
- Chat-2 `ORCHESTRATOR_DIRECTIVE.md` and Chat-6 orchestration state were still formally on `OD-2026-09-29-003 / Pass 3`.

This handoff does not claim that Chat 6 issued a new Pass-7 directive. It records the actual stacked worker pass and its verified GitHub state.

## Delivered functionality

Pass 7 introduces the Phase-B provider-neutral feature snapping baseline without allowing CV to silently rewrite physical truth.

Primary flow:

```text
manual/raw IMAGE_PX anchor
-> detector/provider FeatureSnapCandidate(s)
-> deterministic FeatureAnchorSelector
-> MATCH / NO_MATCH / AMBIGUOUS
-> FeatureSnapProposal
-> explicit user acceptance
-> updated unverified anchor with canonical feature_id
```

## Provider-neutral snapping domain

Added `src/physical_measurement/snapping.py` with:

- `FeatureSnapCandidate`;
- `FeatureAnchorSelector`;
- `FeatureSnapProposal`;
- `FeatureSnapSelection`;
- `SnapSelectionStatus`.

Detector outputs use `VISION_DETECTED` provenance. The selector itself does not depend on OpenCV, a particular ML model, or another detector vendor.

## Deterministic selection rules

- only candidates from the same `view_id` and `reference_frame_id` are eligible;
- only candidates within configured `max_distance_px` are considered;
- nearest geometric distance wins;
- detector confidence is retained but does not override geometric distance;
- candidates within `ambiguity_epsilon_px` of the best distance produce explicit `AMBIGUOUS`;
- no candidate produces `NO_MATCH`;
- duplicate `feature_id` values fail closed.

The selector never invents a feature when evidence is absent or ambiguous.

## Explicit acceptance / physical-truth protection

Added `MeasurementSessionService.apply_anchor_snap()`.

A snap is applied only when:

- `explicit_user_acceptance=True`;
- the measurement is still unverified;
- the target anchor actually belongs to the measurement;
- proposal view/reference matches the target anchor;
- proposal provenance is `VISION_DETECTED`.

Accepted snap behavior:

- preserves logical `anchor_id`;
- updates `x_px` / `y_px`;
- records canonical `feature_id`;
- preserves the measurement's existing value provenance;
- leaves the measurement unverified.

A `VOICE_REPORTED`, `DEVICE_REPORTED`, `OCR_MEASURED` or `MANUAL_MEASURED` value does not become vision-sourced just because its anchor was snapped.

Verified measurements cannot be re-snapped.

## Canonical boundary

`FeatureAnchor` now stores optional `feature_id`.

`CanonicalMeasurementAdapter` serializes accepted feature links directly to canonical `FeatureAnchor.feature_id` while preserving:

- `coordinate_space = IMAGE_PX`;
- raw image coordinates;
- measurement source;
- verification state;
- view/reference linkage.

No geometry normalization was moved into Chat 2 and no canonical contract change was required.

## Files changed in Pass 7

Modified:

- `src/physical_measurement/models.py`
- `src/physical_measurement/service.py`
- `src/physical_measurement/boundary.py`
- `src/physical_measurement/__init__.py`
- `ORCHESTRATOR_HANDOFF.md`

Added:

- `src/physical_measurement/snapping.py`
- `tests/test_pass7_feature_snapping.py`
- `docs/PASS_7_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_7.md`

No file outside `chat_2_physical_measurement/` was modified.

## Build / Reuse

Recorded in `docs/PASS_7_BUILD_REUSE_CHECK.md`.

Decision: PARTIAL reuse. Future edge/corner/keypoint detectors may use OpenCV/ML libraries behind the provider-neutral candidate boundary, while MREA-specific selection/ambiguity/acceptance policy remains local domain/application code.

## Tests added

`tests/test_pass7_feature_snapping.py` verifies:

1. nearest eligible feature wins even if a farther feature reports higher confidence;
2. out-of-threshold and wrong-frame candidates produce `NO_MATCH`;
3. near ties produce `AMBIGUOUS` instead of arbitrary selection;
4. duplicate feature IDs fail closed;
5. anchor mutation requires explicit user acceptance;
6. accepted snap updates coordinates and `feature_id` but does not verify the measurement;
7. original measurement provenance is preserved;
8. canonical output contains accepted `feature_id` with raw `IMAGE_PX` semantics;
9. verified measurements cannot be re-snapped;
10. handcrafted non-vision proposal provenance fails closed.

## GitHub Actions evidence

Executable implementation state:

```text
run_id = 36652682345
run_number = 410
head_sha = 2f45383a685b22508df4b9aa5bf1ea3dbf1a2caf
conclusion = success
```

Required Chat-2 gates executed successfully:

- `Chat 2 / Measurement` — `success`;
- `Contracts / canonical fixtures` — `success`;
- `Integration / Chat 1 -> Chat 2` — `success`;
- `Integration / Chat 2 -> Chat 3` — `success`.

Additional executable slice jobs for Chat 1, Chat 3, Chat 4 generic CAD and Chat 5 also completed successfully. Conditional unrelated integrations may be skipped by repository CI policy.

## Known limitations / next debt

- no actual edge/corner/keypoint detector provider yet;
- no UI overlay/accept-reject interaction layer yet;
- canonical v1 exposes `feature_id` but not anchor-level detector provenance/confidence, so proposal provenance remains internal to the Chat-2 application path;
- snapping remains `IMAGE_PX`-space assistance; geometry normalization remains Chat 3 ownership;
- OCR engine/provider, device/caliper protocol and automatic caliper jaw/contact estimation remain future work;
- legacy `uncertainty_mm` compatibility bridge remains until an explicit cleanup pass.

## Requested integration review

Verify:

1. selector behavior is deterministic and fails closed on no-match/ambiguity;
2. CV candidates cannot silently mutate an anchor without explicit user acceptance;
3. verified measurements cannot be modified by snapping;
4. accepted feature links preserve raw `IMAGE_PX`, measurement provenance and unverified state;
5. canonical adapter emits `feature_id` without shared contract changes;
6. required Chat-2 and adjacent boundary gates are green on implementation SHA `2f45383a685b22508df4b9aa5bf1ea3dbf1a2caf`;
7. worker ownership remains slice-local.

If accepted, integrate after Pass 6 according to orchestrator ordering. This branch is frozen after this handoff commit.
