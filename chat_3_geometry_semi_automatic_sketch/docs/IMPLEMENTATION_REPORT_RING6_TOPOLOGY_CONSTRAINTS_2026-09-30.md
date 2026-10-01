# Chat 3 — Ring 6 Implementation Report — Topology Constraint Candidates

**Date:** 2026-09-30  
**Ring:** 6  
**Branch:** `chat-3/pass-6`  
**Base:** frozen Ring 5 head `f450b3a857fc7353c3b0f8881050cae0ae3199d5`  
**Authorization:** explicit user-requested continuation. `main` still exposed Chat 3 directive OD-2026-09-29-003 when Ring 6 started.

## Objective

Close the next owned Semi-Automatic Sketch gap by extending deterministic geometry relation detection to the remaining canonical v1 constraint families that can be safely inferred without moving geometry:

- `COINCIDENT`;
- `TANGENT`;
- `SYMMETRIC`.

The pass does not add a numerical solver and does not weaken the physical-measurement truth hierarchy.

## Delivered

### Constraint model vocabulary

`ConstraintKind` now covers the complete canonical v1 constraint vocabulary used by Chat 3:

- COINCIDENT;
- HORIZONTAL;
- VERTICAL;
- PARALLEL;
- PERPENDICULAR;
- TANGENT;
- CONCENTRIC;
- EQUAL;
- SYMMETRIC.

No shared schema change was required because these values already exist in canonical `SketchConstraint v1`.

### COINCIDENT candidate generation

`ConstraintCandidateEngine` now generates coincidence only from directly observable finite contact:

- explicit `POINT` lying on another primitive;
- LINE endpoint lying on another supported primitive;
- ARC endpoint lying on another supported primitive;
- endpoint-to-endpoint contact.

A pure intersection between two primitive interiors does **not** become COINCIDENT. This prevents an infinite-line extension or crossing from being silently interpreted as an intended connected topology.

### TANGENT candidate generation

Supported deterministic tangent checks:

- LINE ↔ CIRCLE;
- LINE ↔ ARC;
- CIRCLE ↔ CIRCLE;
- CIRCLE ↔ ARC;
- ARC ↔ ARC.

LINE tangency is finite-segment aware: the perpendicular contact must lie on the observed segment.

ARC tangency is span-aware: the computed tangent point must lie on the observed arc interval.

Round/round tangency supports external and internal tangency and excludes concentric degeneracy.

### SYMMETRIC candidate generation

Symmetry is inferred only when the sketch contains an explicit LINE entity that can serve as the axis.

Ring 6 supports conservative peer pairs:

- POINT ↔ POINT;
- equal-radius CIRCLE ↔ CIRCLE.

The candidate ordering convention is:

```text
(peer_a, peer_b, axis_line)
```

No implicit/imaginary symmetry axis is invented.

### Determinism

All primitives are normalized by `entity_id` before candidate generation.

Candidate IDs are deterministic, and a defensive ID de-duplication boundary prevents repeated endpoint checks from producing duplicate constraints.

Reversing primitive input order produces identical candidates.

### Resolver compatibility / truth hierarchy

Ring 6 reuses the existing `ConstraintResolver` rather than bypassing it.

Therefore new relation candidates still pass through:

- entity existence checks;
- effective confidence gating;
- existing redundancy policy;
- verified-measurement conflict policy where defined.

Effective confidence remains the minimum of candidate and referenced-entity confidence.

The invariant remains:

```text
verified physical measurement > image-derived / geometry-derived relation
```

No constraint candidate moves geometry or changes a verified physical measurement.

## Vision golden change

The existing front-plate image fixture already contains four explicit rectangle corners where detected LINE endpoints meet.

Ring 6 therefore adds four schema-valid inferred COINCIDENT constraints to the canonical vision golden:

- `C_COINCIDENT_L-BOTTOM_L-LEFT`;
- `C_COINCIDENT_L-BOTTOM_L-RIGHT`;
- `C_COINCIDENT_L-LEFT_L-TOP`;
- `C_COINCIDENT_L-RIGHT_L-TOP`.

The existing low-confidence equal-hole relation remains unresolved at confidence `0.766`; verified dimensions remain unchanged.

## Tests

New test module:

`tests/test_topology_constraint_candidates.py`

Coverage includes:

1. endpoint coincidence;
2. rejection of pure interior line crossing as coincidence;
3. explicit POINT-on-CIRCLE coincidence;
4. finite LINE/CIRCLE tangency;
5. LINE/ARC span-aware tangency;
6. external and internal round/round tangency;
7. rejection when a tangent contact lies outside an ARC span;
8. POINT symmetry requiring an explicit axis;
9. CIRCLE symmetry requiring equal radius and reflected centers;
10. deterministic output under primitive reordering.

Existing Ring 4 resolver acceptance was updated to include the four real rectangle corner coincidences.

## Runtime / dependencies

Package version:

```text
0.6.0
```

New Ring 6 dependencies: **none**.

Existing OpenCV dependency remains unchanged.

## Verification

### Local focused verification

```text
28 passed
python -m compileall -q src tests
```

The reconstructed local workspace lacks repository-level shared schemas/fixtures. Its full local run therefore reports `42 passed / 8 failed`, where all eight failures are `FileNotFoundError` for those intentionally absent shared files rather than executable Ring 6 failures.

### GitHub Actions — authoritative repository checkout

Implementation head:

```text
14feaad3e08d622cf17f5f7da60ac09565df908e
```

Workflow run:

```text
36643777256
```

Authoritative Chat 3 result:

```text
50 passed in 0.38s
```

Observed gates:

- `Chat 3 / Geometry`: **SUCCESS — 50 passed**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- `Chat 2 / Measurement`: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: **SUCCESS**;
- `Chat 4 / Generic CAD gate`: **SUCCESS**;
- `Integration / Chat 3 -> Chat 4`: **FAIL only on stale shared test inherited from frozen Ring 5 base**.

## Chat 3 -> Chat 4 baseline drift

The Ring 6 branch inherits the old shared integration test from its frozen Ring 5 ancestry. That old test reads:

```python
transfer.cad_verification_report["dimensions"]
```

and fails with:

```text
KeyError: 'dimensions'
```

after successful SketchPackage generation, schema validation, CAD transfer, CADPackage validation, CADVerificationReport validation and `overall_status == VERIFIED`.

Current `main` has the corrected canonical lookup:

```python
transfer.cad_verification_report["items"]
```

Ring 6 intentionally does not backport or modify Chat-6-owned shared integration infrastructure. Integrator should replay/merge the worker diff onto the current corrected shared baseline.

## Shared ownership

Ring 6 changes no files under:

- `core/contracts/`;
- shared canonical fixtures;
- `tests/integration/`;
- `.github/`;
- Chat 1/2/4/5/6/7/8 directories.

No Change Request was required.

## Known limitations / deferred work

Still deferred:

- numerical constraint solving / entity movement;
- line/arc symmetry beyond the conservative Ring 6 peer set;
- inference of a symmetry axis that is not explicitly represented;
- richer tangent confidence/error models for noisy measurements;
- multi-view geometry relationships;
- CAD-native logic.

## Result

Ring 6 expands Semi-Automatic Sketch from axis/equality relations to explicit topology/tangency/symmetry candidate generation while remaining deterministic, fail-closed and subordinate to verified measurement truth.
