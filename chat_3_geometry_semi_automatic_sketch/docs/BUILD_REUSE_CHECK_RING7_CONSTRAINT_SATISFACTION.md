# Build / Reuse Check — Ring 7 Constraint Satisfaction Diagnostics

**Date:** 2026-09-30  
**Ring:** 7  
**Branch:** `chat-3/pass-7`  
**Base:** frozen Ring 6 head `28d4373b0e9cfdb25a1a833e9ca646c2a06f9d14`  
**Authorization:** explicit user-requested continuation; no newer Chat 3 directive than OD-2026-09-29-003 was present on `main` when Ring 7 started.

## Goal

Prevent stale, manually constructed, or no-longer-valid constraint candidates from being published merely because their ids/types look valid.

Ring 7 adds a read-only geometric satisfaction boundary before `ConstraintResolver` promotion.

## Reuse decision

No new dependency is introduced.

Ring 7 reuses:

- existing POINT / LINE / CIRCLE / ARC models;
- existing `ConstraintCandidate` vocabulary;
- existing `ConstraintResolver` confidence and verified-measurement gates;
- Python standard-library geometry/math;
- existing canonical unresolved mechanism in `SketchPackage v1`.

## Why no numerical solver

A numerical solver would move entities to make constraints true. That is intentionally outside this pass.

Ring 7 only answers:

> Does the current observed geometry already satisfy this candidate relation within an explicit tolerance?

If not, geometry is not moved. The relation becomes explicit unresolved.

## Residual policy

`ConstraintSatisfactionAnalyzer` evaluates canonical v1 relation families.

### Normalized angular residual

Used for:

- HORIZONTAL;
- VERTICAL;
- PARALLEL;
- PERPENDICULAR.

The default tolerance is `1e-3` normalized error.

### Linear residual in mm

Used for:

- COINCIDENT;
- TANGENT;
- CONCENTRIC;
- EQUAL;
- SYMMETRIC.

The default tolerance is `0.05 mm`.

### Topology semantics

COINCIDENT remains finite/observable: endpoint or explicit-point contact is tested. A pure interior/interior line crossing does not satisfy a COINCIDENT candidate.

TANGENT remains finite and arc-span aware.

SYMMETRIC requires the explicit axis line already present in the candidate.

## Resolver policy

Promotion order is:

1. entity existence;
2. effective confidence;
3. geometric satisfaction;
4. redundancy filtering;
5. verified-measurement conflict checks;
6. canonical publication.

An unsatisfied candidate becomes canonical unresolved with code:

`UNSATISFIED_CONSTRAINT`

Verified measurements and entity coordinates remain unchanged.

## Shared ownership

No changes are required to:

- `core/contracts/`;
- canonical fixtures;
- shared integration tests;
- CI;
- other chat directories.

## Decision

**BUILD a small MREA-specific read-only residual analyzer; REUSE the existing resolver and unresolved pipeline; do not introduce a solver dependency.**
