# Build / Reuse Check — Ring 9 Global Constraint-Set Diagnostics

**Date:** 2026-09-30  
**Ring:** 9  
**Branch:** `chat-3/pass-9`  
**Base:** frozen Ring 8 head `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`  
**Authorization:** explicit user-requested continuation; no newer Chat 3 worker directive than OD-2026-09-29-003 was present on `main` when Ring 9 started.

## Goal

Close the next safe part of the deferred "global over-constrained-system diagnosis" gap without pretending that Chat 3 already has a numerical CAD constraint solver.

Ring 9 diagnoses only contradictions and redundancies that can be proven from the accepted constraint graph itself.

## Reuse decision

No external dependency is introduced.

Ring 9 reuses:

- `ConstraintResolver` output from Rings 4–8;
- existing `ResolvedConstraint` confidence/status semantics;
- existing canonical unresolved mechanism through `ConstraintIssue`;
- Python standard-library data structures only.

A full numerical solver is intentionally not introduced because Ring 9 does not move geometry, solve degrees of freedom, or optimize entity positions.

## Orientation graph

The safe global relation subset is:

- `HORIZONTAL`;
- `VERTICAL`;
- `PARALLEL`;
- `PERPENDICULAR`.

They form a binary orientation parity graph:

```text
same orientation        -> parity 0
perpendicular orientation -> parity 1
```

`HORIZONTAL` and `VERTICAL` connect an entity to a virtual world-axis node.

A parity-aware disjoint-set structure detects:

- a relation that adds new independent information;
- a relation already implied by the accepted graph;
- a relation that contradicts the accepted graph.

## Evidence priority

Constraints are processed deterministically by:

1. higher confidence;
2. `DETECTED` before `INFERRED` at equal confidence;
3. direct `HORIZONTAL` / `VERTICAL` before pair relations at equal evidence strength;
4. `constraint_id` as deterministic final tie-breaker.

Therefore a lower-quality relation cannot silently displace stronger accepted evidence.

## Safe transitive redundancy

Ring 9 also removes provably redundant cycles for equivalence relations:

- `EQUAL`;
- `CONCENTRIC`.

No transitivity assumption is applied to:

- `COINCIDENT`;
- `TANGENT`;
- `SYMMETRIC`.

Those relations have semantics where naive graph transitivity would be unsafe.

## Conflict behavior

A proven orientation contradiction is not published. It becomes an explicit canonical unresolved issue:

`OVERCONSTRAINED_ORIENTATION_CONFLICT`

The analyzer does not move entities and does not modify verified physical measurements.

## Scope limit

Ring 9 is **not**:

- a CAD geometric constraint solver;
- a degrees-of-freedom counter;
- a nonlinear optimization engine;
- proof that every mathematically possible overconstraint is detected.

It is a deterministic pre-solver diagnostic layer for contradictions that can be proven from the relation graph.

## Shared ownership

Ring 9 requires no changes to:

- `core/contracts/`;
- canonical shared fixtures;
- `tests/integration/`;
- `.github/`;
- other chat directories.

## Decision

**BUILD a small MREA-specific graph diagnostic layer; REUSE all existing resolver/confidence/satisfaction machinery; do not add a numerical solver or dependency in Ring 9.**
