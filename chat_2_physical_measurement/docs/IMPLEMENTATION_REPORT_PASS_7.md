# Chat 2 — Pass 7 Implementation Report

## Baseline

Pass 7 is stacked on frozen Pass-6 head:

`539d58567046fd29ccf2d42b629227ffe8da6546`

Worker branch:

`chat-2/pass-7`

## Problem closed

Chat 2 already preserved raw `IMAGE_PX` anchors and canonical `feature_id`, but it lacked a safe Phase-B workflow for snapping a manual/raw anchor to a detected image feature.

A detector must never silently rewrite verified physical truth. Pass 7 therefore separates detection/selection from mutation.

## Provider-neutral snapping domain

Added `snapping.py` with:

- `FeatureSnapCandidate` — detector output with `VISION_DETECTED` provenance;
- `FeatureAnchorSelector` — deterministic nearest-feature selector;
- `FeatureSnapProposal` — immutable proposed snap;
- `FeatureSnapSelection`;
- `SnapSelectionStatus`: `MATCH`, `NO_MATCH`, `AMBIGUOUS`.

Selector rules:

1. only candidates from the same `view_id` and `reference_frame_id` are eligible;
2. only candidates inside `max_distance_px` are considered;
3. nearest distance wins;
4. confidence is retained as evidence but does not override geometric distance;
5. candidates within `ambiguity_epsilon_px` of the best distance produce `AMBIGUOUS` instead of an arbitrary winner;
6. duplicate `feature_id` values fail closed.

## Explicit acceptance / physical-truth protection

Added `MeasurementSessionService.apply_anchor_snap()`.

A snap proposal changes an anchor only when:

- `explicit_user_acceptance=True`;
- target measurement is still unverified;
- target anchor exists in that measurement;
- proposal view/reference matches the anchor;
- proposal provenance is `VISION_DETECTED`.

If accepted, the logical `anchor_id` is preserved while `x_px`, `y_px` and canonical `feature_id` are updated.

The measurement value source remains unchanged. A voice/device/manual measurement does not become `VISION_DETECTED` merely because its anchor was snapped.

Most importantly, snapping does **not** set `verified=True`. Measurement verification remains the separate explicit `USER_CONFIRMED` transition.

Verified measurements cannot be re-snapped.

## Canonical boundary

`FeatureAnchor` now owns optional `feature_id`.

`CanonicalMeasurementAdapter` serializes the accepted anchor feature link directly into canonical `FeatureAnchor.feature_id` while preserving:

- `coordinate_space = IMAGE_PX`;
- existing measurement source;
- verification state;
- view/reference linkage.

No `IMAGE_PX -> MAT_XY_MM` normalization was moved into Chat 2.

No canonical contract change was required because `feature_id` already exists in canonical v1.

## Detector ownership

Pass 7 intentionally does **not** implement an OpenCV/ML detector. The detector is a replaceable provider behind `FeatureSnapCandidate`.

This keeps Phase-B correctness independent of a specific CV engine and permits later use of edge/corner/keypoint providers without changing physical-truth policy.

## Tests

Added `tests/test_pass7_feature_snapping.py` covering:

1. nearest eligible feature wins even if a farther feature has higher confidence;
2. out-of-threshold or wrong-frame candidates return `NO_MATCH`;
3. near ties return `AMBIGUOUS`;
4. duplicate feature IDs fail closed;
5. snap mutation requires explicit user acceptance;
6. accepted snap updates coordinates/`feature_id` but keeps measurement unverified and preserves original measurement provenance;
7. canonical output contains accepted `feature_id` in raw `IMAGE_PX` space;
8. verified measurement cannot be modified by snapping;
9. handcrafted proposal with non-vision provenance fails closed.

Existing Phase A / Pass 2 / Pass 3 / Pass 4 / Pass 5 / Pass 6 tests remain part of the Chat-2 suite.

## Ownership

Only `chat_2_physical_measurement/` is modified.

No canonical contract, shared fixture, CI workflow, Chat 3 geometry implementation, or other chat-owned slice was changed.

## Remaining debt

- no actual edge/corner/keypoint detector provider yet;
- no UI overlay/accept-reject interaction layer yet;
- snap provenance is explicit in the proposal/application path, while canonical v1 does not currently expose anchor-level provenance beyond `feature_id`;
- snapping is still `IMAGE_PX`-space assistance; geometry normalization remains Chat 3 ownership;
- OCR/device/caliper providers remain separate future work.
