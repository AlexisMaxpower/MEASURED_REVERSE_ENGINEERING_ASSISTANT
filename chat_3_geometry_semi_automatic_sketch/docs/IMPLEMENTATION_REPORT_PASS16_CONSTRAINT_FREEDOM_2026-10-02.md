# Chat 3 Pass 16 — Local Constraint Freedom / Fully-Constrained Diagnosis

**Date:** 2026-10-02  
**Branch:** `chat-3/pass-16`  
**Worker base:** `chat-3/pass-15` @ `4d4a7a4f3b4b17680dc6eb2c97d337c29ae848ac`  
**Central main observed at start:** `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

## Coordination baseline

At Pass-16 start central `main` still contained the Round-14 closure while Chat 3 already had a published Pass-15 worker branch four commits ahead of that main. Pass 16 therefore extends the exact Pass-15 Chat-3 head rather than discarding already-published Chat-3 work. It remains a worker branch and is not merged directly to `main`.

## Scope

Pass 16 closes the deferred read-only degree-of-freedom accounting gap after Pass 15 global constraint-system diagnosis.

Added public diagnostics:

- `ConstraintFreedomStatus`;
- `ConstraintFreedomIssue`;
- `ConstraintFreedomDiagnosis`;
- `ConstraintFreedomAnalyzer`.

The analyzer:

- parameterizes the existing `POINT`, `LINE`, `CIRCLE`, `ARC` internal geometry;
- maps supported accepted constraints to local scalar equations;
- includes supported verified physical dimensions as equations;
- computes local Jacobian rank deterministically using finite differences + internal elimination;
- reports total local DOF;
- identifies rigid-frame DOF that remain legal;
- reports internal shape DOF separately;
- distinguishes `FULLY_CONSTRAINED`, `CONSTRAINED_UP_TO_FRAME`, `UNDER_CONSTRAINED`, `INDETERMINATE`, and `CONFLICTING`;
- never moves geometry or rewrites a constraint/measurement.

Supported verified dimension semantics in this pass:

- linear distance between supported parallel lines for `LINEAR_EXTERNAL`, `LINEAR_INTERNAL`, `THICKNESS`, `SLOT_WIDTH`;
- Circle diameter;
- Circle/Arc radius;
- Circle-to-Circle center distance.

Unsupported verified dimension semantics, unresolved measurement bindings, ambiguous topology witnesses, or unsupported accepted constraints fail closed to `INDETERMINATE` rather than manufacturing a DOF result.

Existing global constraint conflicts and verified measurement-vs-geometry conflicts block an exact DOF claim.

## Topology witness correction found by CI and leadership audit

The first Pass-16 CI run correctly exposed that generic point-on-line `COINCIDENT` residuals lose rank at an exact zero-distance line-line endpoint intersection. The public freedom analyzer therefore uses a unique endpoint-pair witness for Line-Line `COINCIDENT`, producing the two independent X/Y equations required by topology.

The Orchestrator-2 review tightened this rule further: entity-only `COINCIDENT` does not carry endpoint ordinals, so *nearest proximity alone is not a topology witness*. The selected endpoint pair is accepted only when it is uniquely nearest **and already coincident within `ambiguity_tolerance_mm`**. A unique but spatially separated nearest pair, an ambiguous pair, or an Arc contact without an explicit endpoint/curve witness fails closed to `INDETERMINATE` instead of guessing intended topology.

This is a root-cause correction; the rectangle test was not weakened, and a dedicated leadership regression test covers the separated-line fail-closed case.

## Invariants

- diagnosis is read-only;
- no entity movement or numerical constraint solving is introduced;
- verified measurement values/provenance/uncertainty are not changed;
- global conflicts are not hidden;
- unsupported semantics are not guessed;
- shared contracts and canonical fixtures are unchanged;
- no external dependency was added.

## Runtime / dependencies

Package version: `0.13.0`  
New dependencies: none.

## Verification

Original worker code head before leadership repair:

`dd5595e3961979cc42f71135c99b5cf1ac616b54`

Original worker GitHub Actions:

```text
36933857622  MREA CI  SUCCESS
```

Observed Chat-3 gate on that worker head:

```text
Chat 3 / Geometry  SUCCESS — 141 passed in 0.51s
```

The same worker-head workflow also passed canonical contracts and adjacent worker/generic-CAD gates, including the existing Chat-2 -> Chat-3 and Chat-3 -> Chat-4 integration jobs in the complete workflow.

The authoritative integrated Round-16 candidate includes the later Orchestrator-2 topology-witness repair and must be certified only by CI on that later exact integration SHA; the worker run above is historical evidence only.

## Shared ownership

Pass 16 changes no:

- `core/contracts/`;
- canonical shared fixtures;
- shared integration tests;
- CI workflows;
- CAD-vendor logic;
- other chat-owned directories.

## Deferred Chat 3 work

- actual numerical constraint solving/entity movement;
- explicit DOF semantics for verified angular dimensions;
- explicit arc-contact topology witnesses for DOF accounting;
- richer uncertainty/noise models for contact/angular relations;
- multi-view geometry relationships;
- CAD-native logic.
