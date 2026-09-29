# MREA Orchestration State

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive revision:** `OD-2026-09-29-002`  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** Round 1 reviewed — PARTIAL; Pass 2 directives issued

## Source-of-truth hierarchy
1. Current accepted repository state on `main`.
2. Canonical shared contracts in `core/contracts/`.
3. Canonical fixtures in `tests/fixtures/contracts/`.
4. Chat 6 ADR/review/workflow documents.
5. Product SSOT v0.1 plus orchestration addendum.
6. Slice-local documentation.

If slice-local documentation conflicts with canonical contracts or an active Chat 6 directive, the canonical/Chat 6 source wins.

## Round 1 review

Detailed report:

`chat_6_orchestrator/ROUND_1_REVIEW_2026-09-29.md`

Review cutoff:

`94e6db6a1e2c64c9a3b8d2fca92b7c07acf07d8a`

Overall verdict:

**PARTIALLY ACCEPTED — END-TO-END NOT GREEN**

## Current slice status

- Chat 1: OD-001 ACCEPTED. Canonical Project/Capture and calibration baseline accepted. Pass 2: perspective normalization.
- Chat 2: OD-001 ACCEPTED AS SLICE. Raw IMAGE_PX anchors are intentional. Pass 2: harden real raw measurement output/evidence.
- Chat 3: FIX REQUIRED FOR INTEGRATION. Current adapter accepts only MAT_XY_MM; actual Chat 2 output is IMAGE_PX. Pass 2: homography-based normalization before new CV breadth.
- Chat 4: generic CAD gate ACCEPTED structurally. Real SOLIDWORKS runtime remains unverified. CR-002 resolved by ADR-001. Pass 2: SOLIDWORKS 2026 CAD Agent path.
- Chat 5: OD-001 ACCEPTED WITH PROCESS FIX. Missing Pass-1 handoff noted. Pass 2: CAD verification → lifecycle/manufacturing eligibility linkage.

## Integration status

```text
Chat 1 → Chat 2    PASS (static review)
Chat 2 → Chat 3    FAIL — IMAGE_PX vs MAT_XY_MM integration gap
Chat 3 → Chat 4    PASS at canonical/golden boundary
Chat 4 → Chat 5    NOT IMPLEMENTED in Round 1
```

## Active architectural decisions

- `ADR_001_SOLIDWORKS_2026_CAD_AGENT.md` defines the first real SOLIDWORKS adapter environment.
- Pass 2+ uses per-chat development branches and Chat 6 integration review; see `DEVELOPMENT_WORKFLOW.md`.

## Shared rules

- IDs are opaque non-empty strings. UUIDs are recommended but not required by wire contracts.
- Timestamps are UTC/RFC3339.
- v1 length unit is `mm`; angle unit is `deg`.
- Verified physical measurements are never silently modified by CV/AI.
- Raw measurement anchors may legitimately remain `IMAGE_PX` until a geometry-normalization boundary uses calibration to obtain `MAT_XY_MM`.
- CAD transfer verification is numerical transfer verification, not manufacturing tolerance verification.
- Default CAD transfer tolerance: `1e-6 mm` / `1e-6 deg`.
- SketchPackage v1 mandatory geometry subset: POINT, LINE, CIRCLE, ARC.
- Unsupported/ambiguous geometry is explicit in `unresolved`.
- Worker chats do not modify canonical shared contracts without a Chat 6-approved Change Request.

## Published canonical fixtures
- `tests/fixtures/contracts/project_v1.json`
- `tests/fixtures/contracts/capture_package_v1.json`
- `tests/fixtures/contracts/measurement_package_v1.json`
- `tests/fixtures/contracts/sketch_package_v1.json`
- `tests/fixtures/contracts/cad_package_v1.json`
- `tests/fixtures/contracts/cad_verification_v1.json`
- `tests/fixtures/contracts/lifecycle_event_v1.json`

## Verification note

Round 1 worker-local test results are recorded in their handoff/state documents. Chat 6 did not independently rerun all suites from a clean checkout in this review session, and no GitHub CI status checks were present at the review cutoff. Therefore independent runtime verification remains a future integration responsibility.

## Change control

Any backward-incompatible shared contract change requires a Change Request to Chat 6. Slice-local internal models may evolve independently as long as adapters preserve canonical contracts and active integration invariants.
