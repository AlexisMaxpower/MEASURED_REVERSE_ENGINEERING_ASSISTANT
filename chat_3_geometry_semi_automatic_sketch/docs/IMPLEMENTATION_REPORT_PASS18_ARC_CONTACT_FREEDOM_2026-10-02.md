# Implementation Report — Pass 18 — Arc Contact Freedom

**Date:** 2026-10-02  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Branch:** `chat-3/pass-18`  
**Base:** shared `main` @ `af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`  
**Directive:** `OD-2026-10-02-010`

## Scope

Pass 18 closes the deferred local-DOF gap for explicit contact topology involving trimmed `Arc` entities. It remains a read-only diagnosis feature: geometry is not solved, moved or rewritten.

## Implemented behavior

### Arc-related COINCIDENT

Exact local DOF accepts an Arc-related entity-only `COINCIDENT` relation only when the current geometry exposes one unique endpoint-to-endpoint witness.

The witness is selected deterministically from contact ordinals already exposed by `Point`, `Line` and `Arc`. A unique witness contributes two independent coordinate equations. Endpoint-to-interior contact, a missing witness or multiple equally plausible witnesses fail closed.

This prevents a trimmed Arc from being silently interpreted as an unbounded circle or from inventing an endpoint ordinal that the relation does not contain.

### Line-Arc TANGENT

The existing line-round tangent equation may contribute to exact DOF only when all of the following are true at the current geometry:

- the finite Line is non-degenerate;
- its center-to-line distance matches the Arc radius within the existing numerical witness epsilon;
- the projected tangent contact lies strictly inside the finite Line segment;
- that contact lies strictly inside the Arc trim span;
- the contact is not at an Arc trim boundary.

If any condition is not established, the accepted relation remains unsupported by exact local DOF and diagnosis is `INDETERMINATE`.

### Arc-Circle / Arc-Arc TANGENT

For round-round contact, exact DOF requires exactly one current tangent branch to be established: external or internal. The derived tangent contact must lie strictly inside every Arc trim span participating in the relation.

Concentric/degenerate geometry, no compatible branch, ambiguous branch selection, a contact outside an Arc span, or a contact on a trim boundary fail closed.

## Determinism

Entity ordering does not change the diagnosis for the supported Arc-contact cases. The policy uses deterministic endpoint ordering and the same positive-wrap Arc span convention already used by the Chat-3 dimensioned-view renderer.

## Tests

Added `tests/test_constraint_freedom_arc_contacts.py` covering:

- unique Arc-Line endpoint coincidence;
- unique Arc-Arc endpoint coincidence;
- Arc coincidence without endpoint witness;
- Line-Arc interior tangency;
- tangency outside an Arc trim span;
- tangency at a trim boundary;
- Arc-Circle external tangency inside/outside the Arc span;
- Arc-Arc tangency requiring both spans to contain contact;
- deterministic entity-order behavior.

The code-and-tests head executed the complete Chat-3 suite successfully with **160 passed** before a later documentation/version push superseded that workflow. Final exact-branch-head CI is required before Pass 18 is considered delivered.

## Invariants preserved

- verified physical measurements remain authoritative;
- no geometry entity is moved or solved;
- no verified measurement value, provenance or uncertainty is rewritten;
- no physical tolerance or confidence is invented;
- unsupported or ambiguous topology remains explicit through fail-closed freedom diagnosis;
- shared contracts, canonical fixtures, integration tests and other chat slices are unchanged.

## Package

`mrea-chat3-geometry` version: **0.15.0**  
New dependencies: **none**.

## Deferred

- numerical constraint solving / entity movement;
- coupled endpoint tangency where separate relations explicitly prove that a tangent contact is also a trim endpoint;
- richer uncertainty/noise models for contact and angular relations;
- multi-view geometry relationships;
- CAD-native logic outside Chat-3 ownership.
