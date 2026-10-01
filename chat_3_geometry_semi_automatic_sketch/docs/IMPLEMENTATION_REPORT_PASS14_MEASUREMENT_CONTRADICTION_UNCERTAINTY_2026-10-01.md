# Chat 3 Pass 14 — Uncertainty-Aware Verified-Measurement Contradiction Policy

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-14`  
**Base:** `main` @ `d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`

## Scope

Pass 14 closes the remaining fixed-tolerance gap in the opt-in uncertainty-aware constraint path. Pass 13 already allowed explicit verified measurement uncertainty to widen supported geometric residual tolerances. Pass 14 applies the same evidence discipline to the later verified-measurement contradiction gate without changing legacy `ConstraintResolver` behavior.

## Added capability

New public APIs:

- `MeasurementContradictionPolicy`;
- `UncertaintyAwareMeasurementContradictionPolicy`.

`UncertaintyAwareConstraintResolver` now accepts an optional `measurement_contradiction_policy` and uses it after residual/confidence/redundancy gates.

## Grounded contradiction semantics

### EQUAL

For existing comparable verified intrinsic metrics:

- Circle `RADIUS` uncertainty is direct;
- Circle diameter uncertainty is divided by two because verified comparison is performed in radius units;
- Line linear uncertainty is direct;
- both sides require explicit uncertainty before the contradiction allowance may widen;
- effective allowance is fixed `measurement_tolerance + left_uncertainty + right_uncertainty`;
- if either side lacks uncertainty, the fixed legacy tolerance remains authoritative.

### CONCENTRIC

For a verified `CENTER_DISTANCE` bound to the exact entity pair:

- explicit uncertainty widens the zero-distance contradiction allowance by that uncertainty;
- missing uncertainty preserves fixed legacy behavior.

Any verified measurement still outside its evidence-grounded allowance remains an explicit contradiction and blocks constraint publication with the existing canonical issue code and measurement-id traceability.

## Invariants

- `ConstraintResolver` remains unchanged;
- verified values, units, provenance, flags, geometry, and stored confidence are never mutated;
- uncertainty is never invented;
- relevant uncertainty must be finite, non-negative, and in `mm`;
- invalid relevant uncertainty fails closed;
- no unsupported angular/contact/symmetric uncertainty mapping is introduced;
- no numerical solver or entity movement is introduced.

## Package

`mrea-chat3-geometry` advances from `0.10.0` to `0.11.0`.

New dependencies: none.

## Verification

Implementation head:

`24882183d7f0708a6d3f61cd7d5801868c66b6fa`

GitHub Actions:

`36811263134` — `MREA CI` — `SUCCESS`

Observed required gates:

```text
Chat 3 / Geometry                 SUCCESS — 115 passed in 0.58s
Contracts / canonical fixtures   SUCCESS
Chat 2 / Measurement             SUCCESS
Chat 4 / Generic CAD gate        SUCCESS
Integration / Chat 2 -> Chat 3   SUCCESS — 1 passed in 0.37s
Integration / Chat 3 -> Chat 4   SUCCESS — 1 passed in 2.22s
```

## Ownership

Pass 14 changes no shared contracts, canonical shared fixtures, shared integration tests, CI workflows, CAD-vendor logic, or other chat-owned directories.
