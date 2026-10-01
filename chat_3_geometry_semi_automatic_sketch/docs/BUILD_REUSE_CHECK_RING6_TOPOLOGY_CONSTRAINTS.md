# Build / Reuse Check — Ring 6 Topology Constraint Candidates

**Date:** 2026-09-30  
**Ring:** 6  
**Branch:** `chat-3/pass-6`  
**Base:** frozen Ring 5 head `f450b3a857fc7353c3b0f8881050cae0ae3199d5`  
**Authorization:** explicit user-requested continuation; no newer Chat 3 directive than OD-003 was present on `main` when Ring 6 started.

## Goal

Close the next owned Semi-Automatic Sketch gap by generating conservative candidates for canonical v1 constraint kinds that were still missing from Chat 3:

- `COINCIDENT`;
- `TANGENT`;
- `SYMMETRIC`.

The output remains candidate geometry. It does not move entities and does not override physical measurement truth.

## Reuse decision

No new dependency is introduced.

Ring 6 reuses:

- existing `ConstraintCandidateEngine` as the single candidate-generation boundary;
- existing POINT / LINE / CIRCLE / ARC models;
- existing `ConstraintResolver` for confidence, redundancy and verified-measurement promotion gates;
- Python standard-library math only.

## Why not add a numerical constraint solver

A solver answers a different question: how to move/solve geometry so a set of constraints is satisfied.

Ring 6 only answers:

> Which geometric relationships are already directly supported by the observed geometry within an explicit tolerance?

Adding a solver would increase dependency and semantic surface while risking accidental geometry mutation. Numerical solving remains a later slice.

## Candidate policy

### COINCIDENT

Generate only from observable contact:

- point entity lying on another supported primitive;
- LINE/ARC endpoint lying on another supported primitive;
- endpoint-to-endpoint contact.

No hidden extension-line intersection is promoted as coincidence.

### TANGENT

Generate only when the observed finite primitives support tangency within tolerance:

- LINE ↔ CIRCLE;
- LINE ↔ ARC, with tangent point lying on the observed arc span;
- CIRCLE/ARC ↔ CIRCLE/ARC for external or internal tangency, excluding concentric degeneracy.

### SYMMETRIC

Generate only with an explicit LINE entity acting as symmetry axis.

Ring 6 supports conservative peer pairs:

- POINT ↔ POINT about a LINE;
- CIRCLE ↔ CIRCLE of equal radius about a LINE.

The candidate entity ordering convention is:

```text
(peer_a, peer_b, symmetry_axis_line)
```

The shared contract itself remains unchanged; this convention is slice-local until Integrator review.

## Truth / confidence

Candidate generation does not make a relation verified.

Existing `ConstraintResolver` still computes effective confidence as the minimum of:

- candidate confidence;
- confidence of every referenced entity that exposes confidence.

Low-confidence relations remain explicit unresolved items rather than silently becoming CAD constraints.

Verified physical measurements remain higher priority than geometry-derived/inferred relationships.

## Dependencies

New Ring 6 dependencies: **none**.

Existing OpenCV dependency is unchanged and remains used only by image candidate extraction.

## Shared ownership

Ring 6 does not require changes to:

- `core/contracts/`;
- canonical fixtures;
- shared integration tests;
- CI;
- Chat 1/2/4/5/6/7/8 directories.

## Decision

**REUSE the current candidate/resolution architecture; BUILD only conservative MREA-specific topology relation detection.**
