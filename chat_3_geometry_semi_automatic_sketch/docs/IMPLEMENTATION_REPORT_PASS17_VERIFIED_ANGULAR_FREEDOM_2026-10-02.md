# IMPLEMENTATION REPORT — Chat 3 Pass 17 — Verified Angular Dimension Freedom

**Date:** 2026-10-02  
**Branch:** `chat-3/pass-17`  
**Base:** shared `main` @ `933d925c69944d40859ae1f9ff80d7a3ecb7f760`  
**Directive:** `OD-2026-10-02-009`

## Goal

Close the deferred Pass-16 gap for verified angular-dimension DOF semantics while preserving Chat-3 diagnostic-only and fail-closed behavior.

## Implemented

The public `ConstraintFreedomAnalyzer` now represents a verified `ANGLE` measurement as one local equation when two Line entities expose an unambiguous common endpoint that defines the physical angle vertex.

Key properties:

- endpoint storage direction does not affect the result;
- only the included angle in `[0, 180] deg` is represented;
- explicit measurement uncertainty may admit a compatible current-geometry witness but never rewrites the verified value;
- geometry inconsistent with verified angle beyond that explicit uncertainty fails closed;
- 0/180-degree cases use a non-degenerate cross-product local equation;
- unsupported or ambiguous topology remains `INDETERMINATE` instead of guessing a ray/vertex.

No numerical solver, entity movement, CAD logic or measurement mutation was introduced.

## Tests added / strengthened

Coverage includes:

- one-rank contribution from a verified 90-degree Line-Line angle;
- invariance to reversing both Line endpoint storage directions;
- nonzero local rank at 0 degrees;
- no-shared-vertex fail-closed behavior;
- two-possible-vertices fail-closed behavior;
- mismatch beyond explicit uncertainty fail-closed behavior;
- compatibility within explicit uncertainty;
- invalid unit fail-closed behavior;
- preservation of unverified-dimension behavior and existing Pass-16 regressions.

## Package

`mrea-chat3-geometry` version: `0.14.0`  
New dependencies: none.

## Code-head verification

Code/version head:

`8d37cfb48b043fbb767738c64bfe0fc742842085`

GitHub Actions:

```text
36941003170  MREA CI  SUCCESS
```

Observed:

```text
Chat 3 / Geometry                 SUCCESS — 150 passed in 0.77s
Contracts / canonical fixtures   SUCCESS
Chat 2 / Measurement             SUCCESS
Chat 4 / Generic CAD gate        SUCCESS
Integration / Chat 2 -> Chat 3   SUCCESS
Integration / Chat 3 -> Chat 4   SUCCESS
```

## Ownership

Pass 17 changes only `chat_3_geometry_semi_automatic_sketch/` and does not alter shared contracts, shared fixtures, integration tests, workflows or other worker slices.

## Remaining Chat-3 scope

- numerical constraint solving/entity movement remains deferred;
- explicit arc-contact topology witnesses for DOF accounting remain deferred;
- richer uncertainty/noise models for contact and angular relations remain deferred;
- multi-view geometry relationships remain deferred;
- CAD-native logic remains outside Chat 3.
