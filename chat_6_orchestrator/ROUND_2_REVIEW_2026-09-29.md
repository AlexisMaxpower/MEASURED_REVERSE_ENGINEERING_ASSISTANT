# MREA — Round 2 Integration Review

**Reviewer:** Chat 6 — Orchestrator / Repository Integrator  
**Review date:** 2026-09-29  
**Directive:** `OD-2026-09-29-002`  
**Contract baseline:** `mrea.contracts.v1`  
**Final accepted main SHA:** `d999af158310d3d872098a42691b2edc3ff5ebcb`  
**Final main CI run:** `36611690909`

## Overall verdict

**GREEN FOR SOFTWARE INTEGRATION — ROUND 2 ACCEPTED**

The final assembled `main` passed the complete GitHub-hosted MREA CI suite, including both currently executable real cross-slice gates:

```text
Chat 2 IMAGE_PX measurement output
    -> Chat 3 calibration normalization
    -> MAT_XY_MM geometry input            PASS

Chat 4 generic CAD transfer/verification
    -> Chat 5 lifecycle eligibility
    -> manufacturing allow/block policy    PASS
```

One external environment gate remains intentionally open:

**Real Windows 11 + SOLIDWORKS 2026 COM execution is UNVERIFIED.**

The presence of a C# worker, scripts and protocol tests does not count as real SOLIDWORKS runtime verification.

## Slice verdicts

| Slice | Verdict | Round 2 accepted result |
|---|---|---|
| Chat 1 — Project & Guided Capture | `ACCEPTED` | Deterministic perspective normalization/rectification while preserving the clean reference as immutable evidence. |
| Chat 2 — Physical Measurement | `ACCEPTED` | Raw `IMAGE_PX` measurement/evidence boundary hardened without moving geometry normalization into Chat 2. |
| Chat 3 — Geometry & Sketch | `ACCEPTED` | Round 1 blocker fixed: `IMAGE_PX` anchors are normalized through CapturePackage calibration while verified measurement values/provenance remain unchanged. |
| Chat 4 — CAD Bridge & Verification | `ACCEPTED_WITH_RUNTIME_GATE` | Generic CAD and SOLIDWORKS-agent architecture accepted; real installed SOLIDWORKS execution remains `UNVERIFIED`. |
| Chat 5 — Lifecycle | `ACCEPTED` | CAD verification now controls manufacturing eligibility; failed verification is retained as evidence but cannot silently proceed to manufacturing. |

## Integration matrix

| Boundary | Round 2 status | Evidence level |
|---|---|---|
| Chat 1 -> Chat 2 | `PASS / canonical-static` | IDs/reference-frame/evidence semantics remain compatible; dedicated real producer-consumer CI gate is still missing. |
| Chat 2 -> Chat 3 | `PASS / automated` | Real Chat 2 `IMAGE_PX` output is transformed with non-identity homography and consumed by Chat 3. |
| Chat 3 -> Chat 4 | `PASS / canonical-generic` | SketchPackage v1 is accepted by Chat 4 generic mapping/export pipeline; dedicated real producer-consumer integration test is still missing. |
| Chat 4 -> Chat 5 | `PASS / automated` | Real generic CAD transfer result drives lifecycle manufacturing eligibility and failure blocking. |

## Final CI evidence

The final assembled `main` at `d999af158310d3d872098a42691b2edc3ff5ebcb` completed MREA CI with overall conclusion `success`.

Required software jobs include:

- canonical contract/fixture validation;
- Chat 1 slice tests;
- Chat 2 slice tests;
- Chat 3 slice tests;
- Chat 4 generic CAD tests;
- Chat 5 lifecycle tests;
- `Integration / Chat 2 -> Chat 3`;
- `Integration / Chat 4 -> Chat 5`.

## What Round 2 fixed from Round 1

### 1. Measurement -> Geometry mismatch

Round 1 defect:

```text
Chat 2 emitted IMAGE_PX
Chat 3 only accepted MAT_XY_MM
```

Round 2 correction:

- Chat 2 keeps truthful raw `IMAGE_PX` anchors;
- Chat 3 consumes CapturePackage calibration;
- Chat 3 applies homography and produces `MAT_XY_MM` geometry input;
- measurement IDs, values, verification state and provenance are preserved;
- missing/invalid calibration fails explicitly.

### 2. CAD -> Lifecycle gap

Round 1 had no executable link.

Round 2 adds:

- verified CAD output -> manufacturing eligible;
- failed CAD verification -> evidence retained, manufacturing blocked;
- revision retains CAD package / sketch package / verification report traceability.

### 3. Independent CI

Round 1 depended heavily on worker-reported test results.

Round 2 introduced canonical GitHub Actions CI and real cross-slice integration tests. Worker-reported local tests remain useful evidence, but no longer replace independent CI where CI is executable.

## Process defects discovered during the review

These were orchestration/process defects, not worker-product defects.

### A. Shared CI infrastructure was introduced after Pass 2 branches had already started

This created duplicate Chat-6-owned files in worker branches and avoidable merge conflicts.

**Rule from Pass 3:** all Chat-6 shared infrastructure, contracts, CI, directives and review policy changes must land in accepted `main` **before** Pass N branches are created.

### B. Main moved while review PRs were already open

Several PRs temporarily referenced stale base SHAs.

**Rule from Pass 3:** once review begins, Chat 6 does not mutate shared integration infrastructure mid-review unless an emergency requires restarting the affected review against the new baseline.

### C. A worker branch moved after handoff

A worker added documentation/CI evidence after publishing `ORCHESTRATOR_HANDOFF.md`.

**Rule from Pass 3:** `ORCHESTRATOR_HANDOFF.md` freezes the branch. After handoff, the worker makes no commits until Chat 6 explicitly returns `FIX_REQUIRED` and reopens the branch for correction.

CI evidence after freeze is recorded by Chat 6 centrally; a worker must not move its head merely to record a CI result.

## Remaining technical gates

1. Real SOLIDWORKS 2026 host validation on Windows 11.
2. Dedicated automated Chat 1 -> Chat 2 producer-consumer gate.
3. Dedicated automated Chat 3 -> Chat 4 producer-consumer gate.
4. A complete golden software flow spanning Capture -> Measurement -> Geometry -> generic CAD -> Lifecycle.

These become orchestration priorities for Pass 3.

## Round 2 conclusion

Round 2 is accepted as the first **software-integration-green** round of MREA.

This does **not** mean the product is feature-complete or that real SOLIDWORKS integration is verified. It means the currently implemented software slices and required executable boundaries are compatible on the accepted `main` baseline.