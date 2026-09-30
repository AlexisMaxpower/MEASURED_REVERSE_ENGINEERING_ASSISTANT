# Build / Reuse Check — Ring 10 Structural DOF Audit

**Date:** 2026-09-30  
**Ring:** 10  
**Branch:** `chat-3/pass-10`  
**Base:** frozen Ring 9 head `0b657c07cc6d325be8e813c565fe5ca6bcad309a`

## Goal

Add a truthful degrees-of-freedom diagnostic before any future numerical constraint solver is allowed to move geometry.

## Reuse decision

No new dependency is introduced.

Ring 10 reuses:

- the existing v1 primitive parameterizations;
- Ring 9 globally filtered `ConstraintResolution`;
- bound `DimensionBinding` records;
- Python standard library only.

## Why not add a solver yet

A scalar equation count is not the same thing as numerical Jacobian rank. Degenerate or dependent equations can make a sketch less constrained than a raw count suggests.

Ring 10 therefore implements only statements that are mathematically safe without a solver:

1. primitive parameter count is exact for the current internal representation;
2. each supported constraint receives a conservative *maximum* scalar-equation contribution;
3. each bound dimension contributes at most one scalar equation;
4. if parameters still exceed this maximum equation budget, the sketch is definitely underconstrained;
5. if the equation budget reaches/exceeds the parameter count, Ring 10 does **not** claim that the sketch is fully constrained.

## Primitive parameter counts

- POINT: 2 (`x`, `y`);
- LINE: 4 (`x1`, `y1`, `x2`, `y2`);
- CIRCLE: 3 (`cx`, `cy`, `r`);
- ARC: 5 (`cx`, `cy`, `r`, `start_angle`, `end_angle`).

## Constraint equation upper bounds

- HORIZONTAL: 1;
- VERTICAL: 1;
- PARALLEL: 1;
- PERPENDICULAR: 1;
- TANGENT: 1;
- EQUAL: 1;
- CONCENTRIC: 2;
- COINCIDENT: 2 (safe 2D upper bound for entity-level contact semantics);
- SYMMETRIC: 3 (safe maximum for the currently supported point/circle symmetry family).

Unknown future constraint kinds fail closed with `INDETERMINATE_UNKNOWN_CONSTRAINT_ARITY`.

## Classification

```text
parameter_count > equation_upper_bound
-> DEFINITELY_UNDERCONSTRAINED

parameter_count <= equation_upper_bound
-> NOT_PROVEN_UNDERCONSTRAINED
```

The second state is intentionally not named `FULLY_CONSTRAINED`.

## Integration

`VisionGeometryPipeline.audit_structural_dof(...)` exposes the diagnostic through the existing image-derived pipeline without changing `SketchPackage v1` or the Chat 3 -> Chat 4 wire boundary.

## Shared ownership

No changes are required to:

- `core/contracts/`;
- shared fixtures;
- `tests/integration/`;
- `.github/`;
- any other chat directory.

## Decision

**BUILD a conservative structural DOF lower-bound audit; REUSE existing geometry/constraint/dimension semantics; do not introduce a numerical solver or new dependency in Ring 10.**
