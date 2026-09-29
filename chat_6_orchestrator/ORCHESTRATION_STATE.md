# MREA Orchestration State

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive revision:** `OD-2026-09-29-003`  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** Round 2 ACCEPTED — software integration GREEN; Pass 3 preparation active

## Source-of-truth hierarchy
1. Current accepted repository state on `main`.
2. Canonical shared contracts in `core/contracts/`.
3. Canonical fixtures and Chat-6 integration tests under `tests/`.
4. Chat 6 ADR/review/workflow/CI documents.
5. Product SSOT v0.1 plus orchestration addendum.
6. Slice-local documentation.

If slice-local documentation conflicts with canonical contracts or an active Chat 6 directive, the canonical/Chat 6 source wins.

## Round 2 review

Detailed report:

`chat_6_orchestrator/ROUND_2_REVIEW_2026-09-29.md`

Final accepted product-code main SHA for Round 2:

`d999af158310d3d872098a42691b2edc3ff5ebcb`

Final assembled Round 2 CI run:

`36611690909` — `success`

Overall verdict:

**GREEN FOR SOFTWARE INTEGRATION — ROUND 2 ACCEPTED**

## Current slice status

- Chat 1: Pass 2 `ACCEPTED`. Perspective-normalized derived reference/rectification baseline integrated.
- Chat 2: Pass 2 `ACCEPTED`. Raw `IMAGE_PX` measurement/evidence boundary integrated.
- Chat 3: Pass 2 `ACCEPTED`. Round 1 IMAGE_PX -> MAT_XY_MM integration blocker fixed and integrated.
- Chat 4: Pass 2 `ACCEPTED_WITH_RUNTIME_GATE`. Generic CAD + SOLIDWORKS-agent architecture integrated; real SOLIDWORKS 2026 host execution remains `UNVERIFIED`.
- Chat 5: Pass 2 `ACCEPTED`. CAD verification -> lifecycle/manufacturing eligibility linkage integrated.

## Integration status

```text
Chat 1 -> Chat 2    PASS / canonical-static; dedicated real CI gate still required
Chat 2 -> Chat 3    PASS / automated on final main
Chat 3 -> Chat 4    PASS / canonical-generic; dedicated real CI gate still required
Chat 4 -> Chat 5    PASS / automated on final main
```

## CI baseline

Canonical workflow:

`.github/workflows/ci.yml`

Policy:

`chat_6_orchestrator/CI_POLICY.md`

Current independent checks include:

- canonical contract/fixture validation;
- Chat 1 tests;
- Chat 2 tests;
- Chat 3 tests;
- Chat 4 generic CAD tests;
- Chat 5 tests;
- real Chat 2 -> Chat 3 integration gate;
- real Chat 4 -> Chat 5 integration gate;
- full post-merge run on `main`.

A worker-local claim is not sufficient when the same gate is executable in GitHub Actions.

## Active architectural decisions

- `ADR_001_SOLIDWORKS_2026_CAD_AGENT.md` defines the SOLIDWORKS adapter environment.
- Pass 2+ uses per-chat worker branches and Chat 6-controlled integration.
- Pass 3+ uses branch freeze after handoff; see `DEVELOPMENT_WORKFLOW.md`.
- Chat 6 shared infrastructure must be complete before worker branches are created.

## Shared rules

- IDs are opaque non-empty strings. UUIDs are recommended but not required by wire contracts.
- Timestamps are UTC/RFC3339.
- v1 length unit is `mm`; angle unit is `deg`.
- Verified physical measurements are never silently modified by CV/AI.
- Raw measurement anchors may legitimately remain `IMAGE_PX` until geometry normalization uses calibration to obtain `MAT_XY_MM`.
- CAD transfer verification is numerical transfer verification, not manufacturing tolerance verification.
- Default CAD transfer tolerance: `1e-6 mm` / `1e-6 deg`.
- SketchPackage v1 mandatory geometry subset: POINT, LINE, CIRCLE, ARC.
- Unsupported/ambiguous geometry is explicit in `unresolved`.
- Worker chats do not modify canonical shared contracts without a Chat 6-approved Change Request.
- Publishing `ORCHESTRATOR_HANDOFF.md` freezes the worker branch until Chat 6 verdict.

## SOLIDWORKS runtime gate

Generic CAD logic is independently verified in GitHub-hosted CI.

Real SOLIDWORKS 2026 COM integration remains a separate environment gate because GitHub-hosted runners do not provide installed SOLIDWORKS. It remains `UNVERIFIED` until a controlled Windows 11 + SOLIDWORKS 2026 golden run produces evidence.

## Pass 3 orchestration priorities

1. Add real Chat 1 -> Chat 2 automated boundary coverage.
2. Add real Chat 3 -> Chat 4 automated boundary coverage.
3. Build a complete golden software path across the currently implemented slices.
4. Advance each worker slice without weakening provenance/fail-closed rules.
5. Prepare, but do not fake, the real SOLIDWORKS host validation path.

## Change control

Any backward-incompatible shared contract change requires a Change Request to Chat 6. Slice-local internal models may evolve independently as long as adapters preserve canonical contracts and active integration invariants.
