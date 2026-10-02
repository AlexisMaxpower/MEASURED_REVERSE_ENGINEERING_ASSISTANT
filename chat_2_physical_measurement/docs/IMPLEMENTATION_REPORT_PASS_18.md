# Chat 2 — Pass 18 Implementation Report

## Baseline

Pass 18 starts from accepted shared `main`:

`af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`

Active directive: `OD-2026-10-02-010`.

Round 17 is closed and Pass 17 durable hands-free recovery is already integrated into this baseline.

## Goal

Close the earliest remaining SSOT Phase-B gap in Chat 2: provider-independent feature-anchor snapping around a manual IMAGE_PX pick, without allowing a detector or tie-breaking heuristic to silently create an actionable anchor.

## Implementation

Added `src/physical_measurement/anchor_selection.py` with:

- `ManualAnchorPick` — raw operator IMAGE_PX point;
- `AnchorSnapTarget` — provider-neutral `VISION_DETECTED` feature suggestion;
- `AnchorSnapProposal` — non-mutating nearby-feature proposal;
- `FeatureAnchorSelection` — explicit final placement decision with source/confirmation provenance;
- `FeatureAnchorSelector` — deterministic proposal / keep-raw / explicit-accept workflow;
- `AnchorSelectionError` and `AmbiguousAnchorSnap` fail-closed errors.

## Selection policy

`FeatureAnchorSelector.propose_snap(...)`:

1. validates a positive finite snap radius;
2. rejects duplicate target IDs;
3. ignores targets from another `view_id`;
4. ignores targets from another `reference_frame_id`;
5. ignores targets outside the pixel radius;
6. selects only a unique nearest target;
7. fails closed when multiple targets are equally near.

It never materializes or mutates an anchor.

## Explicit acceptance

`accept_snap(...)` requires `explicit_user_confirmation=True`.

An accepted snap records:

```text
source = VISION_DETECTED
confirmation_source = USER_CONFIRMED
snap_target_id = detected target ID
raw_x_px/raw_y_px = original operator click
x_px/y_px = accepted detected point
```

The detector contribution is therefore not relabelled as manual truth.

`keep_raw(...)` records a manual decision instead:

```text
source = MANUAL_MEASURED
confirmation_source = none
x_px/y_px = raw_x_px/raw_y_px
```

## Materialization boundary

`FeatureAnchorSelection.build_anchor(...)` materializes the chosen IMAGE_PX location into the existing internal `FeatureAnchor` model.

This pass deliberately does not change:

- `FeatureAnchor` persistence schema;
- measurement-session local schema version;
- canonical `MeasurementPackage` schema;
- canonical fixtures;
- shared CI;
- Chat 1/3/4/5 code.

The selection object retains snap provenance in-process. Durable persistence of anchor-selection provenance remains a separate model/schema migration and is not silently introduced here.

## Determinism / fail-closed behavior

Pass 18 explicitly rejects or refuses to guess on:

- equal-distance candidates;
- duplicate target IDs;
- non-finite or negative IMAGE_PX coordinates;
- zero/non-finite snap radius;
- non-`VISION_DETECTED` snap targets;
- snap acceptance without explicit confirmation.

Input order cannot change the chosen target when one unique nearest target exists.

## Tests

Added `tests/test_pass18_anchor_snapping.py` covering:

1. nearest-target determinism independent of input order;
2. view/reference-frame scoping;
3. radius filtering;
4. equal-distance ambiguity;
5. duplicate target-ID rejection;
6. advisory source restriction;
7. explicit confirmation requirement;
8. accepted snap provenance;
9. manual keep-raw fallback;
10. materialized IMAGE_PX coordinates;
11. invalid radius / coordinate fail-closed behavior.

Repository-owned GitHub Actions provides the executable test and adjacent boundary evidence.

## Shared-contract impact

None.

No Change Request is required for this pass.

## Known limitations

- no CV detector is implemented; targets are provider-neutral inputs;
- snap selection metadata is not yet durable inside `FeatureAnchor` / SQLite;
- canonical anchor `feature_id` remains unchanged by this pass;
- no annotation UI is implemented here;
- no line/edge/circle-specific snapping topology is implemented; Pass 18 establishes only point-feature selection policy.
