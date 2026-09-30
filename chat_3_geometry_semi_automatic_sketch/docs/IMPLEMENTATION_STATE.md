# Chat 3 — Implementation State

**Date:** 2026-09-30  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Active branch:** `chat-3/pass-8`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Ring:** 8  
**Authorization:** explicit user-requested continuation; no newer Chat 3 worker directive than OD-2026-09-29-003 was present on `main` when Ring 8 started.

## Baseline

Ring 8 branches from frozen Ring 7 head:

`40340f38974ea71ea626a73d4d7f3c5c271dd086`

## Capabilities through Ring 7

Chat 3 already provides:

- canonical CapturePackage / MeasurementPackage adapter;
- `IMAGE_PX -> MAT_XY_MM` normalization;
- POINT / LINE / CIRCLE / ARC models;
- deterministic GeometryGraph;
- measurement binding and conflict visibility;
- deterministic SketchPackage v1 generation;
- OpenCV LINE/CIRCLE/ARC extraction with `VISION_DETECTED` provenance;
- fail-closed ambiguous geometry handling;
- all canonical v1 constraint candidate families;
- `ConstraintResolver` with confidence, verified-measurement and redundancy gates;
- `ConstraintSatisfactionAnalyzer` with explicit residuals and `UNSATISFIED_CONSTRAINT` diagnostics;
- deterministic SVG Dimensioned View.

## Ring 8 — Residual-Aware Constraint Confidence

New module:

`src/mrea_geometry/constraint_confidence.py`

Public API:

- `ConstraintConfidence`;
- `ConstraintConfidenceModel`.

### Purpose

A relation that only barely satisfies a configured geometric tolerance is no longer treated as equally reliable to an exact relation.

For satisfied geometry:

```text
ratio = clamp(residual / tolerance, 0, 1)
confidence = 1 - (1 - boundary_confidence) * ratio^2
```

Default `boundary_confidence = 0.5`.

### Resolver behavior

Resolver order is now:

1. entity existence;
2. geometric satisfaction;
3. residual-derived confidence;
4. effective confidence gate;
5. redundancy policy;
6. verified measurement conflict policy;
7. canonical publication.

Effective confidence is:

```text
min(candidate confidence, entity confidences, residual-derived confidence)
```

The residual model can only lower confidence; it cannot increase source evidence.

### Distinct fail-closed outcomes

- relation outside tolerance -> `UNSATISFIED_CONSTRAINT`;
- relation inside tolerance but too noisy -> `CONSTRAINT_BELOW_PROMOTION_CONFIDENCE`;
- exact/high-quality relation -> publishable if all other gates pass.

Verified physical measurements remain unchanged and higher priority.

## Runtime / dependencies

Package version:

`0.8.0`

New Ring 8 dependencies: **none**.

## Verification

GitHub Actions implementation run:

- run: `36651103396`;
- implementation head: `1a6b58e6e87786b8e67e6f8525ece98e588dfad3`;
- Chat 3 / Geometry: **65 passed in 0.61s**;
- Contracts: SUCCESS;
- Chat 1: SUCCESS;
- Chat 2: SUCCESS;
- Chat 4 generic CAD: SUCCESS;
- Chat 5: SUCCESS;
- Chat 2 -> Chat 3: SUCCESS.

The worker branch's Chat 3 -> Chat 4 gate still inherits the old shared `cad_verification_report["dimensions"]` lookup; current `main` uses canonical `cad_verification_report["items"]`. Ring 8 does not modify shared integration infrastructure.

## Shared ownership

Ring 8 modifies no:

- shared contracts;
- canonical shared fixtures;
- repository integration tests;
- CI workflow;
- other chat directories.

## Deferred Chat 3 work

- numerical constraint solving/entity movement;
- global over-constrained-system diagnosis;
- uncertainty propagation from calibration/vision into tolerance selection;
- multi-view geometry relationships;
- CAD-native logic.

## Current status

`READY_FOR_RING8_INTEGRATOR_REVIEW`

## Ring 8 documents

- `BUILD_REUSE_CHECK_RING8_RESIDUAL_CONFIDENCE.md`;
- `IMPLEMENTATION_REPORT_RING8_RESIDUAL_CONFIDENCE_2026-09-30.md`;
- `ORCHESTRATOR_HANDOFF.md`.
