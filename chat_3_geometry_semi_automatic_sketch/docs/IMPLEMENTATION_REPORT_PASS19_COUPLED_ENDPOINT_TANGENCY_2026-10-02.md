# Chat 3 — Pass 19 Implementation Report — Coupled Endpoint Tangency

**Date:** 2026-10-02  
**Role:** Geometry & Semi-Automatic Sketch  
**Branch:** `chat-3/pass-19`  
**Direct base:** shared `main` @ `701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`  
**Directive:** `OD-2026-10-02-011`

## Goal

Close the Pass-18 deferred gap for tangency at a trimmed `Arc` endpoint without weakening fail-closed topology semantics and without adding a solver or shared-contract topology field.

Pass 18 correctly rejected entity-only `TANGENT` at an Arc trim boundary. Pass 19 supports the narrow coupled case where a separate resolved `COINCIDENT` relation for the same entity pair provides the missing endpoint topology witness.

## Implemented semantics

### Evidence required

Coupled endpoint tangency is represented only when all of the following are true:

1. ordinary Pass-18 interior tangency does not already apply;
2. the same unordered pair has a resolved `COINCIDENT` relation;
3. current geometry exposes exactly one supported endpoint-to-endpoint coincidence witness;
4. current geometry independently establishes the tangent branch/contact;
5. that contact is the exact same witnessed endpoint within the existing numerical ambiguity tolerance.

No endpoint ordinal, contact branch, physical tolerance, confidence, or geometry is inferred from the existence of `TANGENT` alone.

### Line-Arc

A Line-Arc tangent at a shared endpoint is supported only after the same-pair `COINCIDENT` relation and unique endpoint witness are established. The local tangent equation uses orthogonality of the line ray and the Arc radius at the witnessed endpoint.

### Arc-Arc

An Arc-Arc tangent at a shared endpoint is supported only after the same-pair `COINCIDENT` relation, unique endpoint witness, and unique round-round tangent branch are established. The local tangent equation uses collinearity of the two witnessed radius vectors.

### Explicitly unsupported

- endpoint tangency without same-pair `COINCIDENT`;
- unrelated `COINCIDENT` evidence;
- non-tangent geometry that merely shares an endpoint;
- ambiguous endpoint pairs;
- Arc-Circle boundary tangency, because Circle exposes no endpoint ordinal for entity-only `COINCIDENT` to prove;
- unsupported/degenerate contact geometry.

These cases remain `INDETERMINATE` rather than receiving guessed equations.

## Numerical issue found and corrected during CI

The first Pass-19 implementation reused the inherited squared-distance tangent equations after proving the endpoint topology. GitHub CI correctly exposed a local-rank singularity at the coincident endpoint: the tangent equation was accepted but contributed zero additional Jacobian rank.

The implementation was corrected rather than weakening the tests:

- Line-Arc endpoint tangency now uses line-ray/radius orthogonality;
- Arc-Arc endpoint tangency now uses radius-vector collinearity;
- current-geometry topology/branch witnesses are still required before either equation is admitted.

This preserves one independent local tangent relation at the witnessed endpoint.

## Analyzer context

The base analyzer builds one relation at a time, while this policy needs read-only visibility of sibling resolved relations. Pass 19 scopes the current `ConstraintResolution` through a per-analyzer `ContextVar` during `analyze(...)` and resets it in `finally`.

This is diagnostic context only. It does not mutate the resolution or geometry and does not leak relation evidence across analyzer calls.

## Files

Runtime:

- `src/mrea_geometry/constraint_freedom_coupled_policy.py`;
- `src/mrea_geometry/__init__.py`;
- `pyproject.toml` (`0.16.0`).

Tests:

- `tests/test_constraint_freedom_coupled_endpoint_tangency.py`.

Documentation:

- `docs/BUILD_REUSE_CHECK_PASS19_COUPLED_ENDPOINT_TANGENCY.md`;
- this implementation report;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md`.

## Verification

Corrected implementation head:

```text
13c8e0a86378d7c7f83fc40c4e2c1c6d61b577c8
```

MREA CI:

```text
36952095618
```

Results:

- Chat 3 / Geometry: **SUCCESS — 168 passed in 0.78s**;
- Contracts / canonical fixtures: **SUCCESS**;
- Chat 2 / Measurement: **SUCCESS**;
- Integration / Chat 2 -> Chat 3: **SUCCESS**;
- Chat 4 / Generic CAD gate: **SUCCESS**;
- Integration / Chat 3 -> Chat 4: **SUCCESS**.

The final handoff commit must also receive a green exact-head workflow before Pass 19 is treated as delivered.

## Ownership

Pass 19 changes no shared contracts, canonical shared fixtures, integration tests, CI workflows, or other chat directories.

## Remaining Chat-3 scope

- numerical constraint solving / entity movement;
- richer uncertainty/noise models for contact and angular relations;
- multi-view geometry relationships;
- additional topology-sensitive semantics only when explicit evidence exists;
- CAD-native logic remains outside Chat 3.
