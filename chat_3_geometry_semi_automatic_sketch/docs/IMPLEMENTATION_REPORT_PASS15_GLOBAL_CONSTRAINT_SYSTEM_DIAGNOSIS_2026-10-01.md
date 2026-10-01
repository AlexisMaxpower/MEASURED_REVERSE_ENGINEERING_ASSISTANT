# Chat 3 Pass 15 — Global Constraint-System Diagnosis

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-15`  
**Base:** `main` @ `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

## Scope

Pass 15 adds a read-only whole-system diagnostic layer after constraint promotion. It does not solve or move geometry. Its job is to explain supported structural redundancy and logical conflict before any future numerical solver is allowed to act.

## Added capability

New public APIs:

- `ConstraintSystemStatus`;
- `ConstraintSystemIssue`;
- `ConstraintSystemDiagnosis`;
- `ConstraintSystemAnalyzer`.

Statuses are deliberately narrow:

- `CONSISTENT` — no supported global conflict/redundancy detected;
- `REDUNDANT` — supported redundancy detected with no conflict;
- `CONFLICTING` — supported logical/integrity conflict detected.

`CONSISTENT` does not mean fully constrained and does not imply a degree-of-freedom count.

## Global line-orientation diagnosis

The analyzer builds a deterministic accepted relation graph for:

- `HORIZONTAL`;
- `VERTICAL`;
- `PARALLEL`;
- `PERPENDICULAR`.

Edges carry XOR orientation parity and supporting constraint IDs. A new relation that is already implied is diagnosed as redundant; a new relation that requires the opposite parity is diagnosed as conflicting. This detects direct and transitive orientation cycles without modifying the resolution.

## Equivalence and round-relation diagnosis

The analyzer also detects:

- semantic duplicate relations after normalized entity ordering;
- redundant transitive cycles for `EQUAL` within line-length or round-radius domains;
- redundant transitive cycles for `CONCENTRIC` round-center relations;
- direct or transitive `CONCENTRIC` paths that conflict with `TANGENT` on the same positive-radius round entities;
- duplicate `constraint_id` values as fail-closed identity conflicts;
- missing entity references as explicit integrity conflicts.

`COINCIDENT`, `TANGENT`, and `SYMMETRIC` are not treated as transitive equivalence relations.

## Invariants

- input `GeometryDraft` and `ConstraintResolution` are never mutated;
- no constraint is deleted automatically;
- no geometry coordinate is moved;
- no physical measurement, provenance, confidence, or tolerance is rewritten;
- unsupported logical combinations are not guessed into conflicts;
- all supported issues retain deterministic constraint/entity traceability;
- no shared contract or canonical fixture changes.

## Package

`mrea-chat3-geometry` advances from `0.11.0` to `0.12.0`.

New dependencies: none.

## Verification

Implementation head:

`e736936f62e8e48b933ce872da435e18ce51e11c`

GitHub Actions:

`36815732621` — `MREA CI` — `SUCCESS`

Observed required gates:

```text
Chat 3 / Geometry                 SUCCESS — 130 passed in 0.35s
Contracts / canonical fixtures   SUCCESS
Chat 2 / Measurement             SUCCESS
Chat 4 / Generic CAD gate        SUCCESS
Integration / Chat 2 -> Chat 3   SUCCESS
Integration / Chat 3 -> Chat 4   SUCCESS
```

## Ownership

Pass 15 changes no shared contracts, canonical shared fixtures, shared integration tests, CI workflows, CAD-vendor logic, or other chat-owned directories.
