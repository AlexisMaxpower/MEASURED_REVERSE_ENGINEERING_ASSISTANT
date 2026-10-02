# BUILD / REUSE CHECK — Chat 3 Pass 17 — Verified Angular Freedom

**Date:** 2026-10-02  
**Branch:** `chat-3/pass-17`  
**Direct base:** shared `main` @ `933d925c69944d40859ae1f9ff80d7a3ecb7f760`  
**Directive:** `OD-2026-10-02-009`

## Reused surfaces

Pass 17 extends the accepted Pass-16 diagnostic path rather than introducing a second solver or geometry model.

Reused without redefinition:

- `ConstraintFreedomAnalyzer` local Jacobian/rank machinery;
- `_ParameterLayout` for deterministic entity parameterization;
- `DimensionBinding` verified measurement/provenance surface;
- existing fail-closed `unsupported_dimension_ids` behavior;
- Pass-16 unique Line-Line endpoint topology witness;
- canonical `PhysicalMeasurement.type = ANGLE` and `SketchDimension.type = ANGLE` vocabulary already owned by shared contracts.

## Build decision

Add ANGLE semantics only in the Chat-3 public freedom-policy layer.

A verified ANGLE contributes one local DOF equation only when all of the following are explicit:

1. unit is `deg`;
2. exactly two target entities are `Line`;
3. measured value is finite and within `[0, 180]` degrees;
4. the two lines expose exactly one shared endpoint within the existing topology-witness tolerance;
5. both rays are non-degenerate;
6. current geometry agrees with the verified measurement within explicit measurement uncertainty plus a numerical witness epsilon.

The common endpoint defines the angle vertex. Ray direction is derived from topology, never from arbitrary line `start/end` storage order.

For ordinary angles the residual is based on normalized dot/cosine geometry. At 0/180 degrees a cross-product equation is used to avoid the zero first derivative of the dot/cosine form; the current-angle witness keeps the local branch explicit.

## Fail-closed cases

Exact DOF remains `INDETERMINATE` for the ANGLE binding when topology or semantics are not explicit, including:

- no shared endpoint;
- multiple possible shared endpoints;
- non-Line targets;
- wrong unit;
- invalid/out-of-range value;
- invalid uncertainty;
- degenerate ray;
- image/current geometry inconsistent with verified angle beyond explicit uncertainty.

No tolerance, uncertainty, confidence, endpoint ordinal or angle branch is invented.

## Ownership / dependencies

- shared contracts changed: **no**;
- shared fixtures changed: **no**;
- shared integration tests changed: **no**;
- CI workflow changed: **no**;
- other chat directories changed: **no**;
- new runtime dependencies: **none**.
