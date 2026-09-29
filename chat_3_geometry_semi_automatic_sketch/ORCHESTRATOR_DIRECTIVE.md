# ORCHESTRATOR DIRECTIVE — Chat 3
**Revision:** OD-2026-09-29-002  
**Pass:** 2  
**Owner:** Chat 6  
**Round 1 verdict:** FIX REQUIRED FOR INTEGRATION

Read before Pass 2 implementation.

## Branch policy

Pass 2 work MUST be performed on:

`chat-3/pass-2`

Do not commit Pass 2 implementation directly to `main`.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/capture_package_v1.json`
- `tests/fixtures/contracts/measurement_package_v1.json`

## Canonical output
- `tests/fixtures/contracts/sketch_package_v1.json`

## Round 1 finding

Your deterministic MAT_XY_MM FRONT pipeline is retained, but the real Chat 2 → Chat 3 boundary is not currently compatible.

Actual Chat 2 output legitimately emits raw anchors as:

`coordinate_space = IMAGE_PX`

Current `CanonicalInputAdapter` rejects anything except `MAT_XY_MM`.

The Integrator golden MeasurementPackage masked this because it is already pre-normalized.

## Pass 2 PRIMARY gate — coordinate normalization

Before advanced primitive extraction, make the input boundary support both canonical coordinate spaces.

### MAT_XY_MM anchors

Pass through unchanged.

### IMAGE_PX anchors

When the matching CapturePackage view contains valid calibration:

1. verify anchor `reference_frame_id` matches the view clean-reference artifact;
2. read the matching view homography `IMAGE_PX → MAT_XY_MM`;
3. apply the 3x3 homogeneous transform;
4. perform homogeneous divide safely;
5. reject non-finite/degenerate results;
6. produce internal `Point2D` in MAT_XY_MM;
7. preserve `anchor_id`, `measurement_id`, verified/source semantics and traceability.

If IMAGE_PX is supplied but calibration/homography is missing or invalid, fail explicitly or create an explicit unresolved path. Never guess scale.

## Required tests

Add tests using Chat-2-style wire data rather than only the pre-normalized golden fixture:

- `feature_id = null`;
- IMAGE_PX anchors;
- non-identity homography;
- expected transformed MAT_XY_MM points;
- wrong reference frame rejected;
- missing calibration rejected/unresolved explicitly;
- verified measurement identity/provenance survives transformation;
- deterministic output.

At least one integration test should construct or load a slice-local specimen shaped like the actual Chat 2 canonical adapter output.

## Gate ordering

Do NOT proceed to OpenCV primitive extraction / new detector breadth until this coordinate-normalization gate is green.

Once green, the existing FRONT golden pipeline remains the downstream acceptance test.

## Do not

- modify Chat 2 to hide this integration issue;
- modify canonical contracts for a problem already representable by v1;
- silently overwrite physical values from transformed/image-derived geometry.

## Acceptance target

Demonstrate:

```text
Chat-2-style IMAGE_PX MeasurementPackage
+ calibrated CapturePackage
→ normalized MAT_XY_MM geometry input
→ existing deterministic GeometryPipeline
→ schema-valid SketchPackage
```

## Required handoff

Update `ORCHESTRATOR_HANDOFF.md` with Pass 2 branch, final SHA, exact tests executed, limitations and requested acceptance gate.
