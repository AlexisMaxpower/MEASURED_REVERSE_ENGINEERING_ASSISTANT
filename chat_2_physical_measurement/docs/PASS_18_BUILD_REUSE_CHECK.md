# Chat 2 — Pass 18 Build / Reuse Check

## Baseline

- shared baseline: `main@af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`
- directive: `OD-2026-10-02-010`
- scope owner: Chat 2 / Physical Measurement

## Problem

The accepted repository already contains manual IMAGE_PX anchors, durable measurement sessions, hands-free candidate/confirmation flows and restart recovery. It does not contain the SSOT Phase-B `FeatureAnchorSelector` / snapping workflow.

Adding a CV feature detector in this pass would combine two independent concerns:

1. detecting a candidate feature;
2. deciding whether an operator's manual anchor may snap to it.

That would make the truth boundary provider-dependent and would make it harder to test the user-confirmation requirement independently.

## Reuse decision

Reuse only Python standard-library primitives and existing Chat-2 domain types:

- `FeatureAnchor` for the materialized IMAGE_PX point;
- `ProvenanceSource` for advisory detection and confirmation provenance;
- `math.hypot` for pixel distance;
- immutable dataclasses for provider-neutral inputs/results.

No external geometry, CV, nearest-neighbour, state-machine or UI dependency is justified for deterministic nearest-point snapping over the small candidate set supplied by a future detector.

## Boundary decision

Pass 18 implements only the provider-independent selection policy:

```text
manual IMAGE_PX pick
+ VISION_DETECTED target candidates
-> context/radius filtering
-> unique nearest proposal OR fail closed
-> explicit user accept OR keep raw
-> materialized FeatureAnchor
```

A snap proposal is never an anchor by itself.

Accepted snap provenance remains:

```text
source = VISION_DETECTED
confirmation_source = USER_CONFIRMED
```

Manual keep-raw remains:

```text
source = MANUAL_MEASURED
confirmation_source = none
```

The existing `FeatureAnchor` storage model has no durable selection-provenance fields. Pass 18 therefore does not silently change the private SQLite payload schema or shared canonical contract. The `FeatureAnchorSelection` result keeps the provenance visible to the application layer; a future dedicated migration is required before that metadata can be made durable.

## Rejected alternatives

- silently snap to the first candidate — nondeterministic / order-dependent;
- break equal-distance ties by target ID — deterministic but semantically unjustified;
- allow AI-inferred targets — exceeds the intended vision-detected advisory boundary;
- add a CV library now — detection is a separate SSOT component and high-risk concern;
- change canonical contracts to persist snap metadata — Chat 2 does not own shared contracts.

## Dependency result

No new dependency added.
