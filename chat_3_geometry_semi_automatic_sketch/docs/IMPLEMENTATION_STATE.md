# Chat 3 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Active branch:** `chat-3/pass-2`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Active directive:** `OD-2026-09-29-002`  
**Ring:** 2

## Current status

Round 1 deterministic FRONT pipeline retained. Chat 6 identified the real Chat 2 → Chat 3 integration gap: Chat 2 legitimately emits canonical anchors in `IMAGE_PX`, while Ring 1 `CanonicalInputAdapter` accepted only `MAT_XY_MM`.

Ring 2 closes that boundary before any OpenCV / primitive-extraction expansion.

## Canonical inputs / output

Inputs remain Integrator-owned:

- `/core/contracts/mrea_contracts_v1.schema.json`;
- `/core/contracts/POLICIES_V1.md`;
- `CapturePackage v1`;
- `MeasurementPackage v1`.

Output remains:

- `SketchPackage v1` in `MAT_XY_MM`.

Shared contracts/fixtures are not modified by Chat 3.

## Implemented through Ring 1

- POINT / LINE / CIRCLE / ARC internal primitives;
- `GeometryGraph`;
- deterministic constraint candidates;
- measurement binding;
- verified-vs-derived conflict visibility;
- canonical `SketchPackageBuilder`;
- deterministic entity/dimension ordering;
- exact FRONT golden comparison;
- JSON Schema validation;
- preservation of canonical `measurement_id` links.

## Ring 2 coordinate normalization

`CanonicalInputAdapter` now supports both v1 coordinate spaces.

### MAT_XY_MM

- passed through unchanged;
- does not require homography lookup.

### IMAGE_PX

Adapter:

1. verifies anchor view;
2. verifies `reference_frame_id` equals selected view clean-reference `artifact_id`;
3. requires calibration with `coordinate_system = MAT_XY_MM`;
4. validates exactly 9 finite homography coefficients;
5. rejects degenerate 3x3 matrix;
6. applies projective homogeneous transform;
7. performs safe divide by `w`;
8. rejects non-finite/degenerate output;
9. returns internal `Point2D` in `MAT_XY_MM`.

No scale is guessed.

## Traceability

Internal `AnchorRef` now retains:

- `anchor_id`;
- normalized point;
- `feature_id`;
- `reference_frame_id`;
- `source_coordinate_space`.

Physical `measurement_id`, value/unit, `verified` and source/provenance remain unchanged by coordinate normalization.

## Chat 2 integration specimen

Added:

`tests/fixtures/internal/chat2_image_px_measurement_package.json`

It uses the same essential wire characteristics as actual Chat 2 canonical adapter output:

- `IMAGE_PX`;
- `feature_id = null`;
- clean-reference `reference_frame_id`;
- verified `MANUAL_MEASURED` measurement.

The specimen itself validates against canonical `MeasurementPackage` schema.

## Acceptance path now implemented

```text
Chat-2-style IMAGE_PX MeasurementPackage
        +
CapturePackage with calibration/homography
        ↓
CanonicalInputAdapter
        ↓
MAT_XY_MM AnchorRef / MeasurementRef
        ↓
GeometryPipeline
        ↓
SketchPackageBuilder
        ↓
schema-valid deterministic SketchPackage v1
```

## Verification

Executed full Chat 3 suite against a reconstructed local repository context using exact current Integrator contract blobs:

```text
python -m pytest -q
```

Result:

```text
20 passed in 0.85s
```

Inventory:

- 6 Phase 1 geometry tests;
- 4 canonical FRONT tests;
- 10 Ring 2 coordinate-normalization tests.

Also executed:

```text
python -m compileall -q src tests
```

Result: success.

## Ring 2 explicit failure behavior

Rejected explicitly:

- wrong clean-reference frame;
- missing calibration for IMAGE_PX;
- wrong calibration target coordinate system;
- wrong homography length;
- non-finite coefficients;
- degenerate matrix;
- zero/degenerate homogeneous divisor;
- non-finite homogeneous output;
- unsupported coordinate space.

## Not implemented / intentionally deferred

Per active directive, still deferred:

- raw image contour extraction;
- OpenCV primitive detector;
- detector breadth beyond deterministic fixture output;
- general `ConstraintResolver`;
- inferred-constraint promotion policy;
- Dimensioned View renderer;
- multi-view geometry;
- CAD runtime integration/read-back.

## Shared ownership

Chat 3 does not modify:

- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- directories owned by Chat 1/2/4/5/6.

## Current gate

Requested from Chat 6:

```text
Chat 2 IMAGE_PX output
→ Chat 3 homography normalization
→ MAT_XY_MM geometry pipeline
→ schema-valid SketchPackage
```

Status from Chat 3 side: `READY_FOR_RING2_INTEGRATOR_GATE`.

OpenCV / primitive extraction must not start until Chat 6 accepts this gate.

## Ring 2 documents

- `BUILD_REUSE_CHECK_RING2_COORDINATE_NORMALIZATION.md`;
- `IMPLEMENTATION_REPORT_RING2_COORDINATE_NORMALIZATION_2026-09-29.md`;
- `ORCHESTRATOR_HANDOFF.md`.
