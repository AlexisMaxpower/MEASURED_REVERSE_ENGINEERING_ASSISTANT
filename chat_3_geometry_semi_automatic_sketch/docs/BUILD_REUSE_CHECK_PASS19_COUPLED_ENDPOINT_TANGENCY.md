# Build / Reuse Check — Pass 19 — Coupled Endpoint Tangency

## Decision

Extend the existing read-only `ConstraintFreedomAnalyzer` policy instead of introducing a numerical solver, a new canonical constraint type, or a shared-contract topology field.

## Existing capability reused

Pass 19 reuses:

- Pass-18 explicit Arc endpoint/contact witnesses;
- `ResolvedConstraint` / `ConstraintResolution` as the already-approved relation set;
- existing `COINCIDENT` endpoint-to-endpoint witness logic;
- existing Line-Round and Round-Round tangent equations;
- existing deterministic local Jacobian/rank machinery;
- existing `ambiguity_tolerance_mm` only as a numerical topology-witness tolerance;
- existing global conflict gate and fail-closed unsupported-constraint behavior.

No geometry movement or solve loop is added.

## Gap

Pass 18 correctly rejected `TANGENT` when contact landed on an Arc trim boundary because the entity-only relation did not establish whether that active-set boundary was intentional.

A stronger case is available when the same resolved entity pair also carries `COINCIDENT`, and current geometry exposes one unique endpoint-to-endpoint witness that is the same tangent contact. In that case the separate accepted relation supplies the missing topology evidence without guessing an endpoint ordinal.

## Pass-19 policy

Boundary tangency is admitted only when all required evidence is already present:

1. ordinary Pass-18 interior tangency did not already apply;
2. the same unordered entity pair has a resolved `COINCIDENT` relation;
3. current geometry exposes exactly one supported endpoint-to-endpoint coincidence witness;
4. current geometry independently satisfies the tangent contact branch;
5. the tangent contact equals that exact endpoint witness within the existing numerical ambiguity tolerance.

Supported coupled cases are intentionally narrow:

- Line-Arc endpoint tangency;
- Arc-Arc endpoint tangency.

Arc-Circle boundary tangency remains fail closed because `Circle` has no endpoint ordinal that a separate entity-only `COINCIDENT` relation can prove.

## State / concurrency handling

The public analyzer needs visibility of sibling resolved relations while the inherited equation builder processes one relation at a time. Pass 19 uses a per-analyzer `ContextVar` scoped to `analyze(...)` and resets it in `finally`.

This prevents relation evidence from leaking across analyzer calls and preserves safe reuse under nested/thread/task contexts without changing the base analyzer interface.

## Ownership / dependency check

No changes are required to:

- `core/contracts/`;
- canonical shared fixtures;
- integration tests;
- CI workflows;
- other chat slices;
- runtime dependencies.

The implementation remains entirely inside Chat 3.
