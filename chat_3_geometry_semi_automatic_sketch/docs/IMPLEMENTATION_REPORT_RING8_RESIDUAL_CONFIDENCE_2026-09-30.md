# Chat 3 — Ring 8 Implementation Report — Residual-Aware Constraint Confidence

**Date:** 2026-09-30  
**Ring:** 8  
**Branch:** `chat-3/pass-8`  
**Base:** frozen Ring 7 head `40340f38974ea71ea626a73d4d7f3c5c271dd086`

## Objective

Extend Ring 7 constraint satisfaction diagnostics with deterministic quality scoring for relations that are satisfied but noisy.

Before Ring 8, a candidate inside tolerance could retain confidence `1.0` unless candidate/entity confidence reduced it. Ring 8 makes geometric residual itself contribute to confidence.

## Delivered

### New module

`src/mrea_geometry/constraint_confidence.py`

Public API:

- `ConstraintConfidence`;
- `ConstraintConfidenceModel`.

### Residual-to-confidence mapping

For a satisfied relation:

```text
ratio = clamp(residual / tolerance, 0, 1)
confidence = 1 - (1 - boundary_confidence) * ratio^2
```

Default boundary confidence is `0.5`.

Expected behavior:

- exact -> `1.0`;
- 50% of tolerance -> `0.875`;
- tolerance boundary -> `0.5`;
- unsatisfied/non-finite -> `0.0`.

Zero-tolerance diagnostics only score `1.0` for exact zero residual.

### Resolver integration

`ConstraintResolver` now evaluates candidates in this order:

1. referenced entity existence;
2. current geometry satisfaction;
3. residual-derived geometric confidence;
4. effective confidence gate;
5. redundancy filter;
6. verified-measurement conflict check;
7. canonical publication.

Effective confidence is the minimum of:

- candidate confidence;
- residual-derived geometric confidence;
- confidence of all referenced geometry entities that expose confidence.

Therefore the new model cannot increase confidence above source evidence.

### Issue semantics

- outside satisfaction tolerance -> `UNSATISFIED_CONSTRAINT`;
- inside tolerance but too noisy for current promotion policy -> `CONSTRAINT_BELOW_PROMOTION_CONFIDENCE`.

This distinction is important: the first says the relation is geometrically false under the configured tolerance; the second says it is geometrically acceptable but not reliable enough to publish automatically.

### Shared contract impact

None.

`SketchPackage v1` remains unchanged. Confidence remains internal promotion evidence; canonical constraints keep the current schema.

## Tests

New module:

`tests/test_constraint_confidence.py`

Coverage includes:

1. exact relation scores `1.0`;
2. half-tolerance relation follows quadratic curve;
3. tolerance-boundary confidence is configurable;
4. unsatisfied/non-finite relation scores zero;
5. zero tolerance requires exact relation;
6. resolver rejects a satisfied-but-noisy relation at default `0.95` promotion threshold;
7. same relation can publish under a deliberately lower policy threshold;
8. exact relation remains publishable under default policy;
9. boundary-confidence validation.

Existing Ring 1–7 tests remain part of the same suite.

## Runtime / dependencies

Package version:

`0.8.0`

New Ring 8 dependencies: **none**.

## GitHub Actions verification

Implementation head:

`1a6b58e6e87786b8e67e6f8525ece98e588dfad3`

Workflow run:

`36651103396`

Observed results:

- Chat 3 / Geometry: **SUCCESS — 65 passed in 0.61s**;
- Contracts / canonical fixtures: **SUCCESS**;
- Chat 1 / Capture: **SUCCESS**;
- Chat 2 / Measurement: **SUCCESS**;
- Chat 4 / Generic CAD gate: **SUCCESS**;
- Chat 5 / Lifecycle: **SUCCESS**;
- Integration / Chat 2 -> Chat 3: **SUCCESS**.

### Chat 3 -> Chat 4 inherited baseline issue

The worker ancestry still contains the old Chat-6-owned integration test lookup:

```python
transfer.cad_verification_report["dimensions"]
```

The test reaches successful SketchPackage generation, schema validation, CAD transfer, CADPackage validation, CADVerificationReport validation and `overall_status == "VERIFIED"`, then raises `KeyError: 'dimensions'`.

Current `main` already uses canonical `cad_verification_report["items"]`; Ring 8 does not backport or modify shared integration infrastructure.

## Shared ownership

Ring 8 modifies no:

- shared contracts;
- canonical shared fixtures;
- repository integration tests;
- CI workflow;
- other chat directories.

## Known limitations / deferred work

Still deferred:

- numerical constraint solving/entity movement;
- global over-constrained-system diagnosis;
- uncertainty propagation from calibration/image extraction into per-relation tolerance;
- multi-view geometry relationships;
- CAD-native logic.

## Result

Ring 8 separates three states that were previously too close together:

```text
exact/high-quality relation
    -> publishable

satisfied but noisy relation
    -> confidence-gated

unsatisfied relation
    -> explicit unresolved
```

This improves fail-closed behavior for noisy geometry without weakening verified physical measurement truth.
