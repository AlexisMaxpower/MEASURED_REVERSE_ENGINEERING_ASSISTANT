# ORCHESTRATOR HANDOFF — Chat 3 — Pass 2

**From:** Chat 3 — Geometry & Semi-Automatic Sketch  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Directive:** `OD-2026-09-29-002`  
**Pass / Ring:** 2  
**Branch:** `chat-3/pass-2`  
**Implementation head before handoff commit:** `7fff7d3549fa46f1be32fc563657ec2a8de263bd`  
**Date:** 2026-09-29

> Git commit SHA depends on the committed handoff content itself, so this file records the exact final implementation head immediately before the handoff-only commit. The authoritative final branch SHA including this document is the current `chat-3/pass-2` branch ref reported to Chat 6 together with this handoff.

## Status

`READY_FOR_RING2_INTEGRATOR_GATE`

## Round 1 issue addressed

Round 1 retained the deterministic FRONT pipeline but failed the real Chat 2 → Chat 3 boundary:

```text
Chat 2 canonical output: IMAGE_PX anchors
Chat 3 Ring 1 adapter: MAT_XY_MM only
```

Pass 2 adds the required normalization boundary without changing canonical contracts.

## Delivered functionality

### Canonical coordinate spaces

- `MAT_XY_MM`: pass-through, no homography required.
- `IMAGE_PX`: normalized to `MAT_XY_MM` using the selected CapturePackage view calibration.

### IMAGE_PX safety / validation

- verifies anchor `view_id`;
- verifies `reference_frame_id` equals clean-reference `artifact_id`;
- requires calibration target `MAT_XY_MM`;
- requires exactly 9 finite homography coefficients;
- rejects degenerate 3x3 matrix;
- applies homogeneous transform;
- performs safe divide by `w`;
- rejects zero/degenerate homogeneous divisor;
- rejects non-finite transformed output;
- never guesses scale.

### Traceability

Internal `AnchorRef` retains:

- `anchor_id`;
- normalized point;
- `feature_id`;
- `reference_frame_id`;
- original `source_coordinate_space`.

Measurement identity/value/unit/verified/source semantics survive normalization unchanged.

## Canonical inputs / outputs used

Integrator-owned, consumed without modification:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- canonical `CapturePackage v1`;
- canonical `MeasurementPackage v1`;
- canonical `SketchPackage v1`.

## Files changed / added in Pass 2

Runtime:

- `src/mrea_geometry/contracts.py`;
- `src/mrea_geometry/models.py`.

Tests / specimen:

- `tests/fixtures/internal/chat2_image_px_measurement_package.json`;
- `tests/test_coordinate_normalization.py`.

Documentation:

- `docs/BUILD_REUSE_CHECK_RING2_COORDINATE_NORMALIZATION.md`;
- `docs/IMPLEMENTATION_REPORT_RING2_COORDINATE_NORMALIZATION_2026-09-29.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md`.

## Test inventory

Existing:

- 6 Phase 1 geometry-core tests;
- 4 canonical FRONT schema/golden tests.

Pass 2:

- 10 coordinate-normalization tests.

Pass 2 tests cover canonical Chat-2-style specimen validation, non-identity transform, projective homogeneous divide, clean-reference validation, missing/degenerate calibration failures, MAT_XY_MM pass-through, schema-valid downstream SketchPackage and determinism.

## Tests actually executed

Full Chat 3 suite:

```text
cd chat_3_geometry_semi_automatic_sketch
python -m pytest -q
```

Exact result:

```text
20 passed in 0.85s
```

Compile check also executed:

```text
python -m compileall -q src tests
```

Result: success.

## Test environment note

The sandbox cannot DNS-resolve GitHub for `git clone`. To avoid claiming an unexecuted result, the local test workspace was reconstructed from the verified Ring 1 cumulative snapshot plus exact current Integrator-owned contract/fixture blobs fetched through the connected GitHub API. The executed source payload matches the files committed to this branch.

## Tests not executed

- GitHub Actions: repository has no required Chat 3 CI status gate in this workflow.
- Real camera/image acquisition: outside Pass 2 scope.
- OpenCV primitive extraction: explicitly forbidden until this integration gate is accepted.

## Known limitations

- no calibration-quality threshold is invented locally;
- no multi-view normalization/correspondence;
- no recovery from invalid calibration by guessed scale;
- primitive extraction remains fixture-driven;
- general constraint solver and Dimensioned View remain later work.

## Shared ownership / Change Requests

Shared contracts changed: **none**.

Other chat ownership changed: **none**.

Open Change Requests: **none**. Canonical v1 already represents both coordinate spaces and homography.

## Requested acceptance gate

Please review branch `chat-3/pass-2` for:

```text
Chat-2-style IMAGE_PX MeasurementPackage
+ calibrated CapturePackage
→ normalized MAT_XY_MM geometry input
→ existing deterministic GeometryPipeline
→ schema-valid SketchPackage v1
```

Acceptance should confirm the previously failing integration boundary:

```text
Chat 2 → Chat 3
```

If accepted, the next Chat 3 pass may proceed to the primitive-extraction/OpenCV gate only under a new Chat 6 directive.
