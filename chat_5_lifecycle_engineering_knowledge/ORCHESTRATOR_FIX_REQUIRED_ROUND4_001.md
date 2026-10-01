# ORCHESTRATOR FIX REQUIRED — Round 4 / Chat 5 / 001

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Target slice:** Chat 5 — Lifecycle & Engineering Knowledge  
**Directive:** `OD-2026-09-30-004`  
**Branch:** `chat-5/pass-8`  
**Previous frozen handoff:** `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`  
**Status:** `FIX_REQUIRED` — branch reopened only for this correction

## Evidence

Replacement Round-4 integration candidate:

`b5fdcd6324efd1396a3d57a28fc11e0dd0ba4afd`

Round-4 Truth CI:

`36752208521`

Failed job:

`Integration / Round 4 Chat 4 -> Chat 5 truth`

Failed tests:

- `test_round4_numerically_verified_but_runtime_unverified_is_fail_closed_in_lifecycle_and_read_model`
- `test_round4_numerical_mismatch_is_also_fail_closed_when_runtime_is_unverified`

Observed failure:

```text
TypeError: CADRevisionPreparationService.prepare()
got an unexpected keyword argument 'runtime_evidence'
```

Chat 4 truth at that boundary is explicit:

```text
verification_status = VERIFIED (or FAILED for mismatch)
runtime_status      = UNVERIFIED
real_host_executed  = false
```

## Defect

Chat 5 currently derives manufacturing eligibility only from the canonical numerical CAD verification report. It has no boundary for Chat-4 runtime evidence/status and therefore cannot preserve the distinction between numerical verification and controlled-host runtime verification.

For a runtime-gated CAD origin such as `SOLIDWORKS_2026`, numerical `VERIFIED` with runtime `UNVERIFIED` must not silently become manufacturing-eligible.

This is a lifecycle truth/provenance issue, not permission to fake external SOLIDWORKS validation.

## Required correction

Within Chat-5-owned code only:

1. allow `CADRevisionPreparationService.prepare(...)` to consume explicit runtime evidence/status supplied by the CAD boundary, without importing Chat-4 implementation classes as a hard dependency;
2. normalize and persist at least `VERIFIED`, `FAILED`, `UNVERIFIED` runtime state in the revision/CAD link for runtime-gated origins;
3. preserve runtime state through SQLite persistence and reopen/read-model paths;
4. make manufacturing eligibility fail closed when:
   - canonical numerical verification is not `VERIFIED`; or
   - runtime-gated evidence exists and runtime status is not `VERIFIED`;
5. preserve backward-compatible generic/test-double software flows where no runtime gate is supplied, so existing vendor-neutral regression semantics remain valid;
6. never convert `UNVERIFIED` into `VERIFIED` because a generic numerical report passed;
7. add deterministic Chat-5 tests for:
   - canonical VERIFIED + runtime UNVERIFIED => manufacturing ineligible;
   - canonical FAILED => ineligible;
   - runtime status survives persistence/reopen;
   - existing generic path without runtime evidence remains compatible.

No change to the external real-host truth is authorized:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Out of scope

Do not modify:

- Chat 1–4 code;
- root shared integration tests;
- `.github/workflows/**`;
- Chat-4 runtime evidence generation;
- canonical shared contracts unless a concrete Change Request proves they are insufficient.

## Acceptance gate

Before re-handoff:

- all Chat-5 slice tests must pass;
- persistence/read-model tests must cover the new runtime state;
- update `ORCHESTRATOR_HANDOFF.md` with exact final branch SHA and test results;
- freeze the branch again after handoff.

Chat 6 will replay the corrected Chat-5 owned tree into the official candidate and rerun:

`tests/integration/test_round4_chat4_to_chat5_truth.py`

plus the full Round-4 Truth CI. Do not weaken the shared gate to recover green status.
