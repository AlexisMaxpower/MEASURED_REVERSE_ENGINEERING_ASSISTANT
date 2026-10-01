# Chat 3 Pass 13 — Measurement-Grounded Constraint Uncertainty

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-13`  
**Base:** `main` @ `4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`

## Scope

Pass 13 extends the uncertainty work integrated in Round 12 from geometry-conflict comparison into constraint residual acceptance, while keeping the behavior explicit and opt-in.

## Added capability

New public APIs:

- `ConstraintTolerancePolicy`;
- `UncertaintyAwareConstraintTolerancePolicy`;
- `UncertaintyAwareConstraintResolver`.

The resolver preserves the established constraint-promotion sequence. It obtains the baseline `ConstraintSatisfaction`, applies the optional tolerance policy, then uses the existing satisfaction, residual-confidence, candidate/entity-confidence, redundancy and verified-measurement conflict gates.

## Grounded uncertainty mapping

Uncertainty widens residual tolerance only where a direct verified physical-measurement semantic exists:

- `EQUAL` Circle radius residual:
  - `RADIUS` uncertainty is direct;
  - diameter uncertainty is divided by two;
  - both entities require explicit relevant verified uncertainty;
  - selected entity uncertainties are summed as a deterministic worst-case interval.
- `EQUAL` Line length residual:
  - uses existing Chat-3 intrinsic linear measurement types and requires explicit uncertainty on both entities.
- `CONCENTRIC` center-distance residual:
  - uses only a verified `CENTER_DISTANCE` bound to the same entity pair.

When multiple relevant measurements exist, the smallest explicit uncertainty is chosen deterministically.

No uncertainty is inferred for angular relations, `COINCIDENT`, `TANGENT` or `SYMMETRIC`. ARC equality is not newly mapped because the existing verified intrinsic-metric truth mapping does not define that binding.

## Truth and confidence behavior

- verified measurement values, units, provenance and verified flags are unchanged;
- no uncertainty is fabricated;
- missing relevant uncertainty preserves baseline fixed-tolerance behavior;
- invalid relevant uncertainty or invalid scale fails closed;
- default `ConstraintResolver` behavior is unchanged;
- candidate/entity confidence values are not mutated;
- the existing residual confidence model consumes the effective tolerance, so the residual-derived contribution may change while final confidence remains the existing minimum gate.

## Package

`mrea-chat3-geometry` advances from `0.9.0` to `0.10.0`.

New dependencies: none.

## Verification

Implementation head:

`d24903828692705b653fbf98e74514e3944750bc`

GitHub Actions:

`36806295147` — `MREA CI` — `SUCCESS`

Observed required gates:

```text
Chat 3 / Geometry                 SUCCESS — 101 passed in 0.57s
Contracts / canonical fixtures   SUCCESS
Chat 2 / Measurement             SUCCESS
Chat 4 / Generic CAD gate        SUCCESS
Integration / Chat 2 -> Chat 3   SUCCESS — 1 passed
Integration / Chat 3 -> Chat 4   SUCCESS — 1 passed
```

## Ownership

Pass 13 changes no shared contracts, shared fixtures, integration tests, CI workflows, CAD-vendor logic or other chat-owned directories.
