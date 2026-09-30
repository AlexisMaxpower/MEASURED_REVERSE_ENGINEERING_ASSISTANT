# Chat 2 — Pass 6 Implementation Report

## Baseline

Pass 6 is stacked on frozen Pass-5 head:

`a98699803368ca95d57db623034322fde7146c6b`

Worker branch:

`chat-2/pass-6`

## Problem closed

Canonical v1 defines:

```text
PhysicalMeasurement.anchors: minItems=1, maxItems=3
```

Chat 2 previously required exactly two internal anchors (`anchor_a`, `anchor_b`). That made the internal model narrower than the shared wire contract and prevented truthful one-anchor or three-anchor measurement evidence.

## Implementation

`PhysicalMeasurement` now preserves backward compatibility while representing the full canonical cardinality:

- `anchor_a` remains required;
- `anchor_b` is optional;
- `anchor_c` is optional;
- `anchors` property exposes the ordered 1..3 tuple used at the wire boundary.

Fail-closed rules:

- `anchor_c` cannot be supplied without `anchor_b`;
- anchor IDs must be unique;
- all anchors must match the measurement `view_id`;
- all anchors must use the same reference frame.

No type-specific anchor-count rules were invented because canonical v1 currently constrains only total cardinality, not per-measurement-type semantics.

## Application flow

Updated `MeasurementSessionService`:

- manual/reported/generic candidate APIs keep existing `anchor_a`, `anchor_b` call shape;
- `anchor_b` is now optional;
- optional `anchor_c` is propagated into the model.

Updated `MeasurementCandidateContext` / hands-free controller:

- existing two-anchor contexts remain unchanged;
- one-anchor and three-anchor contexts are supported;
- explicit-confirmation semantics remain unchanged.

## Canonical boundary

`CanonicalMeasurementAdapter` now validates and serializes `measurement.anchors` rather than hard-coding `(anchor_a, anchor_b)`.

Output remains raw `IMAGE_PX`; no Chat-3 geometry normalization moved into Chat 2.

No canonical contract change was required.

## Tests

Added `tests/test_pass6_anchor_cardinality.py` covering:

1. one-anchor candidate serializes as one canonical anchor;
2. existing two-anchor API remains compatible;
3. three-anchor candidate preserves anchor order at the wire boundary;
4. `anchor_c` without `anchor_b` fails closed;
5. duplicate anchor IDs fail closed;
6. third-anchor view/reference mismatches fail closed;
7. hands-free three-anchor context remains an unverified candidate.

Existing Phase A / Pass 2 / Pass 3 / Pass 4 / Pass 5 tests remain part of the Chat-2 suite.

## Ownership

Only `chat_2_physical_measurement/` was modified.

No canonical contracts, shared fixtures, Chat-6 CI, Chat-3 geometry code or other worker slices were changed.

## Remaining debt

- per-measurement-type anchor semantics are still intentionally unspecified because canonical v1 does not define them;
- automatic snapping / feature detection remains future work;
- legacy `uncertainty_mm` compatibility bridge remains until an explicit cleanup pass;
- downstream consumers may still use only a subset of canonical 1..3 cardinality and must fail explicitly if they cannot consume a valid package.
