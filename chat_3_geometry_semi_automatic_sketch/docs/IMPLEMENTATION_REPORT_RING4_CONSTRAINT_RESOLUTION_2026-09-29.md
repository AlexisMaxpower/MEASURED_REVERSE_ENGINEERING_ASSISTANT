# Chat 3 — Ring 4 Implementation Report — Constraint Resolution

**Date:** 2026-09-29  
**Ring:** 4  
**Branch:** `chat-3/pass-4`  
**Base:** frozen Ring 3 head `08e716161a8c9173b7583d6ad87c84c10ddc4221`  
**Authorization:** explicit user request to start Pass 4. No Chat 6 `OD-004` was present on `main` at branch creation.

## Objective

Implement the next Chat 3-owned stage after image-backed primitive extraction:

```text
geometry candidates
        ↓
constraint candidates
        ↓
truth/confidence/redundancy resolution
        ↓
canonical SketchPackage v1 constraints + unresolved
```

The resolver must not change verified measurements or move geometry.

## Delivered

### ConstraintResolver

New module:

`src/mrea_geometry/constraints.py`

New public types:

- `ResolvedConstraint`;
- `ConstraintIssue`;
- `ConstraintResolution`;
- `ConstraintResolver`.

### Promotion rules

Candidate relations are deterministic and pass through the following gates:

1. referenced entities must exist;
2. effective confidence must satisfy threshold;
3. redundant axis-implied pair constraints are omitted;
4. verified measurement conflicts suppress the relation;
5. surviving candidates become canonical constraints.

The resolver never adjusts geometry to make a relation true.

### Confidence propagation

Effective relation confidence is the minimum of:

- candidate confidence;
- confidence of each referenced geometry entity when available.

Default promotion threshold is `0.95`.

This is especially important for Ring 3 vision geometry: two detected circles with entity confidence `0.766` no longer produce a falsely high-confidence `EQUAL` canonical relation. Instead the relation remains explicit unresolved.

### Verified-measurement precedence

`EQUAL` is rejected when verified comparable intrinsic measurements disagree beyond tolerance.

`CONCENTRIC` is rejected when a verified center-distance measurement for the pair is non-zero beyond tolerance.

In both cases the verified measurement is preserved unchanged and the suppressed relation is recorded in `SketchPackage.unresolved`.

### Redundancy / overconstraint control

For axis-aligned geometry:

- HORIZONTAL and VERTICAL single-entity constraints remain publishable;
- pair `PARALLEL` / `PERPENDICULAR` relations already implied by those axis constraints are omitted.

For rotated geometry, where HORIZONTAL/VERTICAL do not apply, valid PARALLEL/PERPENDICULAR relations remain publishable.

### Canonical builder integration

`SketchPackageBuilder.build()` now accepts optional:

```text
constraint_resolution
```

Backward compatibility is preserved:

- callers that omit it still produce `constraints: []`;
- therefore accepted Ring 1 canonical golden behavior is unchanged;
- constraint-aware flows explicitly supply the resolution.

### Constraint-aware vision pipeline

New module:

`src/mrea_geometry/vision_pipeline.py`

The package-level `VisionGeometryPipeline` now composes:

```text
GeometryPipeline
→ ConstraintResolver
→ SketchPackageBuilder(constraint_resolution=...)
→ extraction unresolved merge
```

The Ring 3 detector itself remains unchanged.

## Vision golden update

The Ring 3 front-plate golden now publishes six safe inferred relations:

- EQUAL opposite horizontal sides;
- EQUAL opposite vertical sides;
- HORIZONTAL bottom/top;
- VERTICAL left/right.

The detected-hole EQUAL relation is not published because both CIRCLE entities carry confidence `0.766`, below the `0.95` promotion threshold.

It is preserved as:

```text
CONSTRAINT_BELOW_PROMOTION_CONFIDENCE
```

Verified dimensions remain unchanged:

- width `40.0 mm`;
- height `20.0 mm`;
- hole diameter `8.0 mm`;
- center distance `20.0 mm`.

## Tests added

`tests/test_constraint_resolution.py` covers:

1. safe axis constraint promotion;
2. redundant pair relation removal;
3. rotated non-axis PARALLEL/PERPENDICULAR preservation;
4. verified-diameter conflict blocking EQUAL;
5. verified-center-distance conflict blocking CONCENTRIC;
6. deterministic resolution under reversed primitive order;
7. backward-compatible builder behavior;
8. source-entity confidence limiting promotion.

## Runtime version

`mrea-chat3-geometry` version:

```text
0.4.0
```

New dependencies: none.

## Verification

### GitHub Actions implementation-head gate

Implementation head:

```text
8ca1fa2294467636583eea2340c2c02e7d130cf7
```

Workflow run:

```text
36625586757
```

Observed results:

- `Chat 3 / Geometry` — **SUCCESS: 35 passed in 0.31s**;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 2 / Measurement` — **SUCCESS**;
- `Integration / Chat 2 -> Chat 3` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 3 -> Chat 4` — **FAIL due pre-existing orchestrator-owned integration-test defect**.

### Chat 3 -> Chat 4 external blocker

The cross-slice test successfully:

- builds the Chat 3 SketchPackage;
- validates it against canonical schema;
- executes Chat 4 CAD transfer;
- validates CADPackage;
- validates CADVerificationReport;
- confirms `overall_status == VERIFIED`.

It then fails only because the shared test reads:

```python
transfer.cad_verification_report["dimensions"]
```

while canonical `CADVerificationReport v1` defines the verification array as:

```python
transfer.cad_verification_report["items"]
```

Failure:

```text
KeyError: 'dimensions'
```

This same defect was already observed in Ring 3 and remains outside Chat 3 ownership. Ring 4 does not modify `tests/integration/` or Chat 4/shared contracts.

## Shared ownership

Ring 4 changes no files under:

- `core/contracts/`;
- `tests/fixtures/contracts/`;
- `tests/integration/`;
- Chat 1/2/4/5/6 directories;
- `.github/`.

## Change requests

None. Canonical `SketchConstraint v1` already contains the relation types/status needed for this pass.

## Known limitations / next Chat 3 work

Still deferred:

- full geometric solving / entity movement;
- COINCIDENT/TANGENT/SYMMETRIC generation policy;
- Dimensioned View renderer;
- multi-view constraint relationships;
- CAD-native logic.

The next clean Chat 3 vertical slice is the **Dimensioned View renderer**, unless Chat 6 publishes a different directive.

## Result

Ring 4 closes the previously missing constraint-resolution/promotion layer with explicit measurement and confidence guardrails. Chat 3 unit behavior, canonical contracts, and the upstream Chat 2 -> Chat 3 boundary are green on a real GitHub checkout. Repository-wide green remains blocked only by the pre-existing Chat 6-owned Chat 3 -> Chat 4 test field mismatch.
