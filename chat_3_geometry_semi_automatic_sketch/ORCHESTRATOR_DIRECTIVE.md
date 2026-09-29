# ORCHESTRATOR DIRECTIVE — Chat 3
**Revision:** OD-2026-09-29-002  
**Owner:** Chat 6
**Pass:** 2  
**Branch:** `chat-3/pass-2`

## Round 1 verdict
`FIX_REQUIRED_FOR_INTEGRATION`.

Your deterministic MAT_XY_MM FRONT pipeline is accepted as useful slice work, but the real upstream boundary is not compatible yet.

## Blocking integration defect
Chat 2 canonical output legitimately contains `IMAGE_PX` anchors. Current `CanonicalInputAdapter` rejects anything other than `MAT_XY_MM`.

## Pass 2 priority — do this before new CV breadth
Implement input normalization:
1. accept `MAT_XY_MM` anchors unchanged;
2. accept `IMAGE_PX` anchors when the matching CapturePackage view has valid calibration homography;
3. transform IMAGE_PX → MAT_XY_MM before geometry matching;
4. preserve measurement_id, anchor_id, feature_id, provenance and reference relationships;
5. explicitly reject or mark unresolved when calibration is absent/invalid;
6. add a cross-slice test with a non-identity homography so pass-through cannot accidentally pass;
7. keep SketchPackage output deterministic.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/capture_package_v1.json`
- canonical/raw Chat-2-style MeasurementPackage data.

## Canonical output
- `SketchPackage v1` in `MAT_XY_MM`.

## CI gate
The repository-level test `tests/integration/test_chat2_to_chat3_boundary.py` is now a required gate and intentionally reproduces the Round 1 defect. Push only to `chat-3/pass-2`; the pass is not integration-acceptable until this job is green.

## Do not
- require Chat 2 to falsify anchors as MAT_XY_MM;
- modify shared contract vocabulary without Change Request;
- silently use identity transform when calibration is missing;
- start advanced primitive/CV expansion before this integration gate is green;
- commit Pass 2 implementation directly to `main`.

## Handoff
Finish with `ORCHESTRATOR_HANDOFF.md` including local and GitHub Actions results.
