# ORCHESTRATOR HANDOFF — Chat 2

**Pass:** 6  
**Branch:** `chat-2/pass-6`  
**Baseline:** frozen Pass-5 head `a98699803368ca95d57db623034322fde7146c6b`  
**Executable implementation SHA:** `b5f7a85c66a0c72aa41edd1b045fa5a9f474b9e7`  
**Implementation CI:** `MREA CI` run `36651166396` / run #360  
**Date:** 2026-09-30  
**From:** Chat 2 — Physical Measurement  
**To:** Chat 6 / integration review

> This handoff is the final worker commit for Pass 6. The branch is frozen after this file update. No post-handoff worker commit should be added unless integration review explicitly returns a fix request.

## Delivered functionality

Pass 6 aligns Chat 2 internal measurement anchors with canonical v1 cardinality.

Canonical v1 allows:

`PhysicalMeasurement.anchors = 1..3`

Before this pass Chat 2 required exactly two internal anchors. Pass 6 preserves existing callers while supporting the complete canonical range.

Internal compatibility shape:

- `anchor_a` — required;
- `anchor_b` — optional;
- `anchor_c` — optional;
- `measurement.anchors` — ordered canonical 1..3 tuple.

## Fail-closed anchor invariants

- `anchor_c` cannot appear without `anchor_b`;
- anchor IDs must be unique;
- every anchor must match measurement `view_id`;
- every anchor must use the same reference frame.

No per-measurement-type anchor-count rule was invented because the current canonical contract only specifies total cardinality 1..3.

## Application flow

`MeasurementSessionService` now accepts one, two or three anchors while preserving the old two-anchor API unchanged.

`MeasurementCandidateContext` / hands-free flow now propagates optional `anchor_b` and `anchor_c` without changing provenance or explicit-confirmation semantics.

## Canonical boundary

`CanonicalMeasurementAdapter` now validates and serializes `measurement.anchors` instead of hard-coding `(anchor_a, anchor_b)`.

Wire invariants remain unchanged:

- anchors stay raw `IMAGE_PX`;
- `feature_id` remains `null` until a later feature-linking pass;
- evidence/view/reference linkage is preserved;
- no geometry normalization moved from Chat 3 into Chat 2;
- candidates remain unverified until explicit user confirmation.

No canonical contract change was required.

## Files changed in Pass 6

Modified:

- `src/physical_measurement/models.py`
- `src/physical_measurement/service.py`
- `src/physical_measurement/hands_free.py`
- `src/physical_measurement/boundary.py`
- `ORCHESTRATOR_HANDOFF.md`

Added:

- `tests/test_pass6_anchor_cardinality.py`
- `docs/PASS_6_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_6.md`

No file outside `chat_2_physical_measurement/` was modified.

## Build / Reuse

Recorded in `docs/PASS_6_BUILD_REUSE_CHECK.md`.

Decision: no third-party library. This is a local domain cardinality migration directly defined by canonical v1.

## Tests added

`tests/test_pass6_anchor_cardinality.py` verifies:

1. one-anchor candidate serializes canonically;
2. old two-anchor API remains compatible;
3. three-anchor candidate preserves ordered wire anchors;
4. `anchor_c` without `anchor_b` fails closed;
5. duplicate anchor IDs fail closed;
6. third-anchor view/reference mismatch fails closed;
7. hands-free three-anchor context remains an unverified candidate.

## GitHub Actions evidence

Executable implementation state:

```text
run_id = 36651166396
run_number = 360
head_sha = b5f7a85c66a0c72aa41edd1b045fa5a9f474b9e7
```

Required Chat-2 gates executed successfully:

- `Chat 2 / Measurement` — `success`;
- `Contracts / canonical fixtures` — `success`;
- `Integration / Chat 1 -> Chat 2` — `success`;
- `Integration / Chat 2 -> Chat 3` — `success`.

Conditional downstream jobs not selected for a Chat-2 worker push may remain skipped by repository CI policy and are not used as this acceptance gate.

## Known limitations / next debt

- canonical v1 does not yet define per-measurement-type anchor-count semantics;
- automatic feature snapping / `feature_id` assignment remains future work;
- legacy `uncertainty_mm` compatibility bridge remains until an explicit cleanup pass;
- downstream consumers that cannot handle a valid 1- or 3-anchor package must fail explicitly rather than silently rewrite it.

## Requested integration review

Verify:

1. canonical 1..3 anchor cardinality is represented truthfully;
2. existing two-anchor callers remain compatible;
3. one/three-anchor packages serialize as raw `IMAGE_PX` without normalization;
4. provenance/confirmation behavior did not regress;
5. required Chat-2 and adjacent boundary CI gates are green on implementation SHA `b5f7a85c66a0c72aa41edd1b045fa5a9f474b9e7`;
6. worker ownership remains slice-local.

If accepted, integrate after Pass 5 according to orchestrator ordering. This branch is frozen after this handoff commit.
