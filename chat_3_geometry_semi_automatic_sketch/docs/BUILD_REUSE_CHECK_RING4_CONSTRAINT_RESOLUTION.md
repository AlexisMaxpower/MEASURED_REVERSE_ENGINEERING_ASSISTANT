# Build / Reuse Check — Ring 4 Constraint Resolution

**Date:** 2026-09-29  
**Ring:** 4  
**Branch:** `chat-3/pass-4`  
**Authorization:** user-requested Pass 4; no `OD-2026-09-29-004` was present on `main` when the branch was created.

## Goal

Close the next Chat 3-owned gap after real image candidate extraction: deterministic promotion of internal geometry relations into canonical `SketchPackage v1.constraints` without allowing inferred geometry to override verified physical measurements.

## Reuse decision

No new external geometry solver is introduced.

Ring 4 reuses existing Chat 3 components:

- `ConstraintCandidateEngine` for deterministic candidate generation;
- `GeometryPipeline` for draft construction and measurement binding;
- `GeometryConflictDetector` for verified-vs-derived metric conflicts;
- `SketchPackageBuilder` for canonical serialization;
- Ring 3 `ImageGeometryExtractor` and OpenCV boundary unchanged.

## Why not add a solver library

This pass does not solve or move CAD geometry. Its responsibility is narrower:

1. inspect already-observed relation candidates;
2. reject weak, redundant, missing-entity, or measurement-conflicting candidates;
3. publish only safe canonical constraint records;
4. preserve rejected evidence as explicit `unresolved` items.

A numerical/geometric solver would add dependency and lock-in without addressing the actual product-policy problem.

## New MREA-specific logic

Ring 4 builds a slice-local `ConstraintResolver` because the rules are MREA-specific:

- verified physical measurement has priority over inferred relation;
- source-entity confidence limits relation confidence;
- weak relations are explicit unresolved, not silently accepted;
- redundant axis-implied relations are omitted to reduce downstream overconstraint;
- relation promotion is deterministic;
- resolver never changes entity coordinates or verified dimension values.

## Confidence policy

Effective constraint confidence is:

```text
min(candidate confidence, confidence of every referenced entity that has confidence)
```

Default promotion threshold:

```text
0.95
```

A relation below the threshold becomes:

```text
CONSTRAINT_BELOW_PROMOTION_CONFIDENCE
```

This prevents a high-confidence derived relation object from laundering lower-confidence vision entities into an apparently certain CAD constraint.

## Measurement guardrails

### EQUAL

If two entities have verified comparable intrinsic measurements and those measurements differ beyond the resolver tolerance, `EQUAL` is not published.

Unresolved code:

```text
VERIFIED_MEASUREMENT_CONTRADICTS_EQUAL_CONSTRAINT
```

### CONCENTRIC

If a verified center-distance measurement for the entity pair is non-zero beyond tolerance, `CONCENTRIC` is not published.

Unresolved code:

```text
VERIFIED_MEASUREMENT_CONTRADICTS_CONCENTRIC_CONSTRAINT
```

## Redundancy policy

When single-entity axis constraints already express the same fact:

- `PARALLEL` between two HORIZONTAL lines is omitted;
- `PARALLEL` between two VERTICAL lines is omitted;
- `PERPENDICULAR` between a HORIZONTAL and VERTICAL line is omitted.

For rotated geometry, where axis constraints do not exist, valid `PARALLEL` / `PERPENDICULAR` candidates remain publishable.

## Canonical compatibility

No canonical contract changes are required.

`SketchConstraint v1` already supports:

- `HORIZONTAL`;
- `VERTICAL`;
- `PARALLEL`;
- `PERPENDICULAR`;
- `CONCENTRIC`;
- `EQUAL`;
- status `INFERRED` / `DETECTED`.

`SketchPackageBuilder` remains backward compatible: if no `ConstraintResolution` is explicitly supplied, canonical constraints remain empty as in the accepted Ring 1 golden fixture.

## Dependencies

New dependencies: **none**.

Existing Ring 3 dependency retained:

```text
opencv-python-headless >=4.10,<5
```

## Decision

**REUSE existing candidate generation and canonical builder; BUILD only the MREA-specific deterministic promotion/truth policy.**
