# Build / Reuse Check — Chat 3 Pass 13 — Measurement-Grounded Constraint Uncertainty

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-13`  
**Baseline:** current certified `main` at `4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`

## Problem

Pass 12 integrated an opt-in uncertainty-aware comparison for verified physical dimensions versus derived geometry. Constraint satisfaction still uses fixed residual tolerances even when the relation has directly relevant verified dimensional uncertainty.

Blindly applying any measurement uncertainty to any geometric relation would be unsafe: a diameter uncertainty does not define an angular tolerance, and a thickness uncertainty does not automatically define tangent/contact uncertainty.

## Reuse decision

Reuse existing Chat-3-owned structures and extension points:

- `DimensionBinding.uncertainty` and verified measurement provenance;
- `ConstraintSatisfaction` residual/tolerance diagnostics;
- `ConstraintSatisfactionAnalyzer` as the baseline geometric residual source;
- `ConstraintResolver` as the promotion boundary;
- existing `ConstraintConfidenceModel` and candidate/entity confidence gates.

No third-party dependency, shared contract, canonical fixture, CI workflow, CAD-vendor logic or cross-chat API is required.

## Selected scope

Add an explicit opt-in `UncertaintyAwareConstraintTolerancePolicy` and `UncertaintyAwareConstraintResolver`. The policy is applied after baseline residual computation and before the existing satisfaction/confidence gates.

The policy may widen only linear `mm` tolerance where canonical measurement semantics directly match the residual:

1. `EQUAL`
   - circle radius equality: `RADIUS` uncertainty is used directly;
   - `DIAMETER_EXTERNAL` / `DIAMETER_INTERNAL` uncertainty is divided by two because the residual is radius difference;
   - line-length equality follows the existing Chat-3 verified line-metric mapping for linear measurements;
   - both compared entities must have an explicit relevant verified uncertainty;
   - the worst-case interval contribution is the sum of the two selected uncertainties; no Gaussian/statistical assumption is invented.

2. `CONCENTRIC`
   - only an explicit verified `CENTER_DISTANCE` measurement bound to the same entity pair may widen the center-distance residual tolerance.

For multiple relevant verified measurements, the smallest explicit uncertainty is selected deterministically as the strongest available measurement precision.

ARC equality is deliberately not uncertainty-mapped in this pass because the existing verified intrinsic-metric mapping used by constraint truth checks covers Circle and Line, not Arc. Pass 13 does not invent a new measurement-binding semantic to extend that boundary.

## Deliberate non-mapping

Do not infer uncertainty conversion for:

- `HORIZONTAL` / `VERTICAL` / `PARALLEL` / `PERPENDICULAR` normalized angular residuals;
- `COINCIDENT`;
- `TANGENT`;
- `SYMMETRIC`.

Those relations require a separate observation/noise model rather than borrowing unrelated dimensional uncertainty.

## Truth / confidence invariants

- measured values, units, provenance and verified flags are never changed;
- uncertainty is consumed only when explicitly supplied;
- missing uncertainty preserves baseline fixed-tolerance behavior;
- invalid negative/non-finite relevant uncertainty fails closed;
- stored candidate/entity confidence is never changed;
- residual-derived confidence consumes the effective tolerance, and final resolved confidence remains the existing minimum of candidate, entity and residual-derived contributions;
- policy is opt-in, so the established default resolver semantics remain unchanged.

## Build decision

Implement this as Chat-3-owned deterministic policy code plus regression tests. No external library is justified.

## Non-goals

- no numerical constraint solver or entity movement;
- no probability distribution fitting;
- no inferred/default uncertainty;
- no unit conversion beyond the exact diameter-to-radius factor required by the existing residual definition;
- no shared schema changes;
- no CAD-native behavior.
