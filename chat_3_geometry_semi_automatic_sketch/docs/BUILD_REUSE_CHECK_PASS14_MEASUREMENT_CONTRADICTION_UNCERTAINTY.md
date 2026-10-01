# Build / Reuse Check — Chat 3 Pass 14 — Measurement Contradiction Uncertainty

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-14`  
**Baseline:** certified `main` at `d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`

## Problem

Pass 13 made geometric constraint residual acceptance uncertainty-aware, but the later verified-measurement contradiction gate still compares verified measurements with a fixed `measurement_tolerance`. That can reject an otherwise valid `EQUAL` or `CONCENTRIC` relation even when the verified measurements themselves explicitly overlap within their stated uncertainty.

The opposite failure is also unsafe: treating missing uncertainty as permission to widen a contradiction band would weaken verified physical truth without evidence.

## Reuse decision

Reuse existing Chat-3-owned structures and semantics:

- `DimensionBinding.value`, `unit`, `verified`, `measurement_type`, `target_entity_ids`, and `uncertainty`;
- existing Circle radius / diameter and Line length verified-metric mapping;
- existing `ConstraintIssue` contradiction codes and measurement-id traceability;
- `UncertaintyAwareConstraintResolver` as the opt-in promotion path introduced in Pass 13;
- existing fixed `ConstraintResolver` behavior as the compatibility baseline.

No shared contract, canonical fixture, CI workflow, third-party dependency, CAD-vendor logic, or cross-chat API is required.

## Selected scope

Add a Chat-3-owned measurement-contradiction policy used only by `UncertaintyAwareConstraintResolver`.

### EQUAL

For comparable verified intrinsic metrics:

- Circle `RADIUS` uncertainty is used directly;
- Circle diameter uncertainty is divided by two because the comparison metric is radius;
- Line linear uncertainty is used directly;
- both compared measurements must carry explicit relevant uncertainty before uncertainty can widen the contradiction allowance;
- when both uncertainties exist, the deterministic allowance is:

`measurement_tolerance + left_uncertainty + right_uncertainty`.

If either side lacks explicit uncertainty, the established fixed `measurement_tolerance` remains authoritative.

### CONCENTRIC

For a verified `CENTER_DISTANCE` bound to the exact same entity pair:

- explicit uncertainty may widen the zero-distance contradiction allowance to `measurement_tolerance + uncertainty`;
- missing uncertainty preserves the fixed baseline behavior.

## Determinism and fail-closed rules

- only verified measurements participate;
- relevant uncertainty must be finite, non-negative, and expressed in `mm`;
- invalid relevant uncertainty fails closed;
- unrelated measurements never influence the contradiction decision;
- when several comparable measurements exist, every contradictory pair/measurement remains traceable through the existing issue `measurement_ids`;
- input measurements, geometry, candidate confidence, provenance, and verified flags are never mutated.

## Compatibility

- `ConstraintResolver` is unchanged;
- callers that do not opt into `UncertaintyAwareConstraintResolver` keep exact fixed-tolerance semantics;
- Pass-13 residual-tolerance behavior remains unchanged;
- no numerical solver or entity movement is added.

## Build decision

Implement the policy in Chat-3-owned Python with regression tests and public exports. Advance only the Chat-3 package version.

## Non-goals

- no probabilistic distribution fitting;
- no default/inferred uncertainty;
- no uncertainty model for angular/contact/symmetric constraints;
- no shared schema changes;
- no CAD-native behavior;
- no global over-constrained-system solver.
