# MREA — Round 1 Integration Review

**Reviewer:** Chat 6 — Orchestrator / Repository Integrator  
**Review date:** 2026-09-29  
**Review cutoff:** `94e6db6a1e2c64c9a3b8d2fca92b7c07acf07d8a`  
**Directive reviewed:** `OD-2026-09-29-001`  
**Contract baseline:** `mrea.contracts.v1`

## Overall verdict

**PARTIALLY ACCEPTED — END-TO-END NOT GREEN**

Round 1 produced useful and mostly well-isolated slice baselines. Ownership discipline was respected: changes since the R0 contract baseline were confined to Chat 1–5 areas; canonical contracts/fixtures were not redefined by worker chats.

The round cannot be declared end-to-end accepted because the real Chat 2 → Chat 3 boundary is currently incompatible:

```text
Chat 2 output anchors: IMAGE_PX
Chat 3 accepted anchors: MAT_XY_MM only
```

The canonical schema intentionally allows both coordinate spaces. The integration fix belongs primarily to Chat 3 because Chat 3 receives both CapturePackage calibration and MeasurementPackage anchors and is the layer that normalizes geometry into `MAT_XY_MM`.

A second missing end-to-end link is expected rather than a regression: Chat 4 → Chat 5 was not part of OD-001 and is not implemented yet.

## Slice verdicts

| Slice | Verdict | Round 1 result |
|---|---|---|
| Chat 1 — Project & Guided Capture | ACCEPTED | Canonical Project/Capture boundary and ChArUco calibration baseline delivered. |
| Chat 2 — Physical Measurement | ACCEPTED AS SLICE | Canonical MeasurementPackage output delivered; IMAGE_PX is valid and intentionally preserved. |
| Chat 3 — Geometry & Sketch | FIX REQUIRED FOR INTEGRATION | Golden MAT_XY_MM FRONT flow exists, but it rejects actual Chat 2 IMAGE_PX output. |
| Chat 4 — CAD Bridge & Verification | ACCEPTED FOR GENERIC CAD GATE | Generic CAD/test-double boundary is structurally sound; real SOLIDWORKS runtime remains unverified. |
| Chat 5 — Lifecycle | ACCEPTED WITH PROCESS FIX | Canonical LifecycleEvent adapter delivered; required ORCHESTRATOR_HANDOFF.md was not provided. |

## Integration matrix

| Boundary | Status | Finding |
|---|---|---|
| Chat 1 → Chat 2 | PASS — static review | Clean-reference artifact IDs and measurement-frame IDs match Chat 2 evidence/reference expectations. |
| Chat 2 → Chat 3 | FAIL | Chat 2 emits IMAGE_PX; Chat 3 hard-requires MAT_XY_MM. |
| Chat 3 → Chat 4 | PASS AT CANONICAL/GOLDEN BOUNDARY | Chat 3 targets canonical SketchPackage v1 consumed by Chat 4. |
| Chat 4 → Chat 5 | NOT IMPLEMENTED | CAD verification is not yet linked to lifecycle revision/manufacturing eligibility. |

## Chat 1 review

Accepted for OD-001.

Observed implementation:

- canonical ProjectContract/CapturePackage builder;
- stable project/part linkage;
- clean reference and measurement frame separation;
- content-addressed artifacts and SHA-256 integrity;
- ChArUco calibration using OpenCV;
- IMAGE_PX → MAT_XY_MM homography stored in CapturePackage calibration;
- schema-validation tests and synthetic calibration test.

Chat 1 reports `13 passed`. The code and tests are consistent with that claim, but Chat 6 did not independently rerun the suite in this review session.

Pass 2 target: deterministic perspective-normalized derived reference artifact with explicit source → derived provenance.

## Chat 2 review

Accepted for OD-001 as a slice.

Important behavior is correct: manual anchors remain raw `IMAGE_PX`; Chat 2 does not silently apply image calibration and therefore does not falsify measurement provenance.

Chat 2 reports `9 passed`. Static review confirms its canonical test explicitly asserts IMAGE_PX output and validates MeasurementPackage against the shared schema.

This behavior exposed an integration gap in Chat 3; it is not a reason to rewrite Chat 2 into a geometry-normalization layer.

Pass 2 target: harden the real raw MeasurementPackage boundary and provide a slice-local integration specimen/test representative of actual Chat 2 output.

## Chat 3 review

Round 1 geometry work is useful but not integration-accepted.

Positive findings:

- deterministic canonical FRONT pipeline;
- POINT/LINE/CIRCLE/ARC support;
- GeometryGraph;
- measurement binding and conflict visibility;
- verified measurements preserved;
- deterministic SketchPackage builder;
- exact golden tests against canonical fixture.

Blocking finding:

`CanonicalInputAdapter.from_packages()` rejects any anchor whose `coordinate_space != MAT_XY_MM`, while Chat 2's canonical adapter intentionally emits IMAGE_PX.

The shared fixture masked this gap because `measurement_package_v1.json` is already pre-normalized to MAT_XY_MM.

Required Pass 2 fix:

1. accept MAT_XY_MM anchors unchanged;
2. accept IMAGE_PX anchors when matching CapturePackage view has valid calibration homography;
3. transform IMAGE_PX to MAT_XY_MM before geometry matching;
4. preserve measurement/provenance/reference IDs;
5. explicitly reject or mark unresolved when calibration is absent/invalid;
6. add a cross-slice test using Chat-2-style IMAGE_PX data and a non-identity homography;
7. do not start advanced primitive extraction until this gate passes.

## Chat 4 review

Accepted for the generic CAD gate, subject to independent runtime verification later.

Positive findings:

- canonical SketchPackage mapper;
- POINT/LINE/CIRCLE/ARC support;
- deterministic SVG;
- DXF via `ezdxf` with parse-back validation;
- vendor-neutral CadAdapter/read-back boundary;
- dimension_id ↔ measurement_id ↔ vendor ref traceability;
- numerical verification with explicit VERIFIED/MISMATCH/MISSING/CONSTRAINT_CONFLICT;
- no silent correction policy;
- deterministic TEST_DOUBLE pipeline.

Chat 4 reports a 23-test inventory, with partial recorded runtime evidence, but a fresh full 23-test run was not independently executed by Chat 6. No GitHub status checks were present at the review cutoff.

`CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md` is resolved by `ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`.

## Chat 5 review

Accepted for OD-001 with a process correction.

Positive findings:

- canonical thin LifecycleEvent adapter;
- deterministic event ordering;
- event-type-specific required references;
- timezone-aware serialization;
- internal failure evidence retained;
- revision/manufacturing/install/failure flow tested.

Chat 5 reports `8 passed`. Static review is consistent with the acceptance target.

Process defect: unlike Chats 1–4, Chat 5 did not publish `ORCHESTRATOR_HANDOFF.md`. This is mandatory from Pass 2 onward.

Pass 2 target: link verified CAD output to lifecycle revision/manufacturing eligibility.

## Test / verification limitation

This review is based on repository state, source/tests, canonical fixtures and handoff evidence. Chat 6 did not obtain an executable clean checkout during this review session, and the repository had no CI status checks at the cutoff commit. Therefore no slice is being credited with an independently rerun Chat-6 test suite.

Reported local test results are preserved as slice evidence, not upgraded into independent orchestration evidence.

## Process change for Pass 2+

Pass 1 is retained on `main` as the accepted development baseline.

Starting with Pass 2:

- each worker chat develops on its own branch;
- worker chats do not commit Pass 2 implementation directly to `main`;
- Chat 6 reviews branch diff, contracts, tests and handoff;
- only Chat 6 integration acceptance moves work into `main`;
- shared contracts remain Chat 6-owned.

See `DEVELOPMENT_WORKFLOW.md`.

## Pass 2 priority

The next round prioritizes integration gaps over new feature breadth:

1. Chat 3 fixes IMAGE_PX → MAT_XY_MM normalization.
2. Chat 4 receives the real SOLIDWORKS environment baseline and begins adapter implementation behind the existing boundary.
3. Chat 5 links CAD verification to lifecycle eligibility.
4. Chat 1 advances perspective normalization.
5. Chat 2 hardens raw measurement output/evidence without absorbing geometry responsibilities.
