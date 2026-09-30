# Build / Reuse Check — Ring 8 Residual-Aware Constraint Confidence

**Date:** 2026-09-30  
**Ring:** 8  
**Branch:** `chat-3/pass-8`  
**Base:** frozen Ring 7 head `40340f38974ea71ea626a73d4d7f3c5c271dd086`  
**Authorization:** explicit user-requested continuation; no newer Chat 3 worker directive than OD-2026-09-29-003 was present on `main` when Ring 8 started.

## Goal

Close the next noisy-geometry gap without adding a numerical solver: a relation that is technically inside the allowed satisfaction tolerance should not automatically carry the same confidence as an exact relation.

Ring 8 therefore derives an additional confidence contribution from the already-computed geometric residual.

## Reuse decision

No new dependency is introduced.

Ring 8 reuses:

- `ConstraintSatisfactionAnalyzer` from Ring 7;
- existing `ConstraintResolver` promotion gate;
- existing candidate confidence;
- existing entity confidence;
- Python standard library only.

A new small MREA-specific policy class is appropriate because the mapping from accepted residual to publishable confidence is product semantics rather than a generic numerical solving problem.

## Confidence policy

For a satisfied relation with residual `r` and tolerance `t`:

```text
ratio = clamp(r / t, 0, 1)
confidence = 1 - (1 - boundary_confidence) * ratio^2
```

Default:

```text
boundary_confidence = 0.5
```

Consequences:

- exact relation (`r = 0`) -> `1.0`;
- half tolerance -> `0.875` with default policy;
- tolerance boundary -> `0.5`;
- unsatisfied/non-finite relation -> `0.0`;
- zero tolerance requires exact residual zero.

The quadratic shape keeps very small residual noise close to 1.0 while penalizing candidates that only barely satisfy a permissive tolerance.

## Resolver composition

The confidence model never increases evidence strength.

Effective confidence remains fail-closed:

```text
effective = min(
    candidate confidence,
    all referenced entity confidences,
    residual-derived geometric confidence,
)
```

The existing `minimum_confidence` gate then decides publication.

## Truth hierarchy

This change does not alter the main invariant:

```text
verified physical measurement > image/geometry-derived relation
```

No measurement or geometry entity is moved or rewritten.

## Why not add a solver or probabilistic library

Ring 8 scores quality of an already observed relation. It does not optimize entity positions or infer a posterior geometry distribution.

A solver or probabilistic dependency would introduce unnecessary complexity and could blur the current separation between observation, confidence, diagnostics and future entity movement.

## Shared ownership

Ring 8 requires no changes to:

- `core/contracts/`;
- shared fixtures;
- `tests/integration/`;
- `.github/`;
- other chat directories.

## Decision

**REUSE Ring 7 satisfaction residuals; BUILD only a deterministic residual-to-confidence policy and compose it into the existing resolver.**
