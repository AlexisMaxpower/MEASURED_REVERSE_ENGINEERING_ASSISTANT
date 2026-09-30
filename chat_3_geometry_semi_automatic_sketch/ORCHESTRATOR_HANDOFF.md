# ORCHESTRATOR HANDOFF — Chat 3 — Pass 8

**From:** Chat 3 — Geometry & Semi-Automatic Sketch  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Pass / Ring:** 8  
**Branch:** `chat-3/pass-8`  
**Branch base:** frozen Ring 7 head `40340f38974ea71ea626a73d4d7f3c5c271dd086`  
**Implementation/docs head before handoff commit:** `642280fb1fe087a470b255c698f46e16c2a69537`  
**Date:** 2026-09-30

## Authorization / baseline note

Ring 8 was started by explicit user instruction. At start, current `main` still exposed Chat 3 directive `OD-2026-09-29-003`; no newer Chat 3 worker directive had been published.

To preserve user-authorized Rings 4–7 work, `chat-3/pass-8` was created directly from frozen Ring 7 head.

No shared contracts, CI, integration tests or other chat-owned files were modified.

## Status

`READY_FOR_RING8_INTEGRATOR_REVIEW`

## Delivered functionality

Ring 8 adds deterministic residual-aware confidence to constraint promotion.

New module:

`src/mrea_geometry/constraint_confidence.py`

Public types:

- `ConstraintConfidence`;
- `ConstraintConfidenceModel`.

## Confidence semantics

For a satisfied relation:

```text
ratio = clamp(residual / tolerance, 0, 1)
confidence = 1 - (1 - boundary_confidence) * ratio^2
```

Default:

```text
boundary_confidence = 0.5
```

Result:

- exact relation -> `1.0`;
- half tolerance -> `0.875`;
- tolerance boundary -> `0.5`;
- unsatisfied/non-finite -> `0.0`.

## Resolver integration

Constraint promotion now distinguishes:

```text
outside tolerance
→ UNSATISFIED_CONSTRAINT

inside tolerance but low residual quality
→ CONSTRAINT_BELOW_PROMOTION_CONFIDENCE

high-quality satisfied relation
→ eligible for remaining gates
```

Effective confidence is the minimum of:

- candidate confidence;
- all referenced entity confidences;
- residual-derived confidence.

The new confidence model cannot strengthen evidence and cannot override verified measurements.

## Truth hierarchy

Unchanged:

```text
verified physical measurement > image/geometry-derived relation
```

No entity movement and no numerical solving are introduced.

## Runtime / dependencies

Package version:

`0.8.0`

New dependencies: **none**.

## Tests

New acceptance module:

`tests/test_constraint_confidence.py`

It verifies exact, partial-tolerance, boundary, non-finite and zero-tolerance scoring plus resolver behavior under different promotion thresholds.

## GitHub Actions verification

Authoritative implementation head:

`1a6b58e6e87786b8e67e6f8525ece98e588dfad3`

Workflow run:

`36651103396`

Results:

- `Chat 3 / Geometry`: **SUCCESS — 65 passed in 0.61s**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- `Chat 1 / Capture`: **SUCCESS**;
- `Chat 2 / Measurement`: **SUCCESS**;
- `Chat 4 / Generic CAD gate`: **SUCCESS**;
- `Chat 5 / Lifecycle`: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: **SUCCESS**.

## Chat 3 -> Chat 4 inherited baseline drift

The frozen worker ancestry still contains the old shared integration-test field lookup:

```python
transfer.cad_verification_report["dimensions"]
```

The boundary run reaches successful SketchPackage generation, canonical validation, CAD transfer, CADPackage validation, CADVerificationReport validation and `overall_status == "VERIFIED"`, then fails with `KeyError: 'dimensions'`.

Current `main` already uses canonical:

```python
transfer.cad_verification_report["items"]
```

Chat 3 did not backport or modify Chat-6-owned shared integration infrastructure.

## Shared ownership / Change Requests

Shared contracts changed: **none**.  
Shared canonical fixtures changed: **none**.  
Shared integration tests changed: **none**.  
CI changed: **none**.  
Other chat directories changed: **none**.  
Change Requests: **none**.

## Integrator review target

Validate on the current shared baseline:

```text
constraint candidate
→ satisfaction residual
→ residual-derived confidence
→ min(candidate/entity/geometric confidence)
→ promotion threshold
→ canonical constraint or explicit unresolved
```

Confirm that exact geometry remains deterministic and that verified measurements remain unchanged.

## Known limitations / next owned work

Deferred unless Chat 6 reprioritizes:

- numerical constraint solving/entity movement;
- global over-constrained-system diagnosis;
- uncertainty propagation from calibration/vision into tolerance selection;
- multi-view relationships;
- CAD-native logic.

## Branch freeze

This handoff is the final normal worker commit for Ring 8.

After publication, `chat-3/pass-8` is treated as **frozen** pending Chat 6 verdict or explicit user/orchestrator instruction.

The only permitted post-handoff write is a minimal repair if the mandatory final GitHub upload audit proves that a claimed Ring 8 file failed to land or differs from intended payload. Any such repair must itself be re-audited.
