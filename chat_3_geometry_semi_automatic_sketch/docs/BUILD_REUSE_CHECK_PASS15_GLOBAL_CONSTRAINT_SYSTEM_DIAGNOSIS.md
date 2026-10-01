# Build / Reuse Check — Chat 3 Pass 15 — Global Constraint-System Diagnosis

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-15`  
**Baseline:** certified `main` at `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

## Problem

Chat 3 already validates individual constraint candidates and preserves verified measurement truth, but there is no explicit whole-system diagnostic after promotion. A set can therefore be individually valid while still containing structural redundancy or mutually incompatible relation declarations supplied through a custom/extended resolution path.

Numerical solving must not be introduced before the system can deterministically explain whether the published relation set is structurally consistent.

## Reuse decision

Reuse existing Chat-3-owned surfaces:

- `GeometryDraft.entities` as the authoritative current geometry snapshot;
- `ConstraintResolution.constraints` as the already-promoted relation set;
- `ResolvedConstraint.constraint_id`, `kind`, and `entity_ids` for deterministic identity;
- existing primitive classes (`Line`, `Circle`, `Arc`) for relation-domain checks;
- existing deterministic ordering conventions.

No shared contract, canonical fixture, CAD-vendor logic, numerical solver, third-party dependency, or cross-chat API is required.

## Selected scope

Add a read-only `ConstraintSystemAnalyzer` with explicit diagnostic output.

### Logical conflict detection

Fail closed for supported relation systems that contain:

- `HORIZONTAL` and `VERTICAL` parity that cannot coexist on the same connected line-orientation graph;
- `PARALLEL` / `PERPENDICULAR` parity cycles that contradict earlier accepted line-orientation relations, including transitive conflicts;
- round entities that are directly or transitively `CONCENTRIC` while also constrained `TANGENT`;
- references to entities absent from the analyzed draft;
- duplicate `constraint_id` values whose identity cannot be diagnosed unambiguously.

These are system-level conflicts; the analyzer reports them but never mutates or silently drops constraints.

### Structural redundancy detection

Report constraints that add no new structural relation because they are:

- semantic duplicates of an earlier deterministic relation;
- line-orientation relations already implied by `HORIZONTAL` / `VERTICAL` / `PARALLEL` / `PERPENDICULAR` paths;
- transitive cycle edges for equivalence-like `EQUAL` or `CONCENTRIC` relations.

`COINCIDENT`, `TANGENT`, and `SYMMETRIC` are deliberately not treated as transitive equivalence relations.

Redundancy is diagnostic only. It does not claim that the sketch is fully constrained, nor does it remove constraints.

## Status semantics

The analyzer reports exactly one system status:

- `CONSISTENT` — no supported structural conflict or redundancy detected;
- `REDUNDANT` — one or more supported redundant constraints detected and no conflict;
- `CONFLICTING` — one or more supported logical/integrity conflicts detected.

`CONSISTENT` does not mean fully constrained; degree-of-freedom solving remains deferred.

## Determinism and fail-closed rules

- input resolution and geometry are never mutated;
- analysis order is stable by `constraint_id`;
- relation paths are deterministic and preserve supporting constraint IDs;
- issue IDs and referenced constraint/entity IDs are deterministic;
- unsupported relation combinations are not guessed into conflicts;
- missing entity references and duplicate constraint IDs are explicit conflicts rather than ignored data;
- no physical measurement value, provenance, confidence, tolerance, or geometry coordinate is rewritten.

## Build decision

Implement the analyzer in a new Chat-3-owned module, export it publicly, add regression tests, and advance only the Chat-3 package version.

## Non-goals

- no entity movement;
- no numerical/Jacobian solver;
- no degree-of-freedom count;
- no automatic constraint deletion;
- no probabilistic inference;
- no shared `SketchPackage` schema change;
- no CAD-native over-definition handling;
- no multi-view solving.
