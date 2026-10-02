# Build / Reuse Check — Pass 18 — Arc Contact Freedom

**Date:** 2026-10-02  
**Branch:** `chat-3/pass-18`  
**Base:** shared `main` @ `af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`  
**Directive:** `OD-2026-10-02-010`

## Problem

Pass 16 introduced read-only local constraint-freedom / DOF diagnosis. Pass 17 added verified angular-dimension semantics. The remaining local-DOF gap selected for Pass 18 was contact topology involving trimmed `Arc` entities.

The numerical core already had equations for generic line-round and round-round tangency and generic endpoint/contact coincidence. Those equations are valid for full round geometry, but applying them to an `Arc` without proving that the current contact lies on the trimmed arc would silently treat the Arc as a full circle.

## Reuse decision

Reuse the existing Chat-3 freedom-analysis machinery rather than add a general CAD constraint solver or another numerical dependency.

Reused components:

- `_ParameterLayout` and its deterministic Arc endpoint reconstruction;
- existing finite-difference Jacobian and rank engine;
- existing line-round and round-round tangent equations;
- existing numerical witness tolerances (`ambiguity_tolerance_mm`, `degenerate_epsilon`);
- the existing Arc span convention already used by `DimensionedViewRenderer`: `(end_angle_deg - start_angle_deg) % 360`.

## Build decision

Add a narrow policy layer in `constraint_freedom_policy.py` that proves topology before an existing equation is allowed to contribute to exact DOF.

Implemented witnesses:

1. Arc-related `COINCIDENT` is accepted only for one unique endpoint-to-endpoint witness.
2. Line-Arc `TANGENT` is accepted only when the current tangent contact is strictly inside both the finite Line segment and the Arc trim span.
3. Arc-Circle / Arc-Arc `TANGENT` is accepted only when exactly one current external/internal tangent branch is numerically established and every Arc involved contains the contact strictly inside its trim span.

Anything else remains unsupported and therefore `INDETERMINATE` in exact freedom diagnosis.

## Why not a general solver

A general sketch solver would introduce entity movement, convergence policy, branch selection, tolerance ownership and potentially upstream-truth mutation concerns that are outside this pass. Pass 18 is diagnostic only and needs no dependency capable of modifying geometry.

## Lock-in / fallback

Lock-in is low. The witness layer is Chat-3-local and sits above the existing numerical core. A future solver can consume the same explicit topology semantics or replace the local rank backend without changing canonical shared contracts.

## Dependency result

New runtime dependencies: **none**.
