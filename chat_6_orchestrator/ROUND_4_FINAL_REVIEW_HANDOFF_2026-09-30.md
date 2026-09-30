# MREA — Round 4 Final Review Handoff

**From:** Chat 6 — Orchestrator / Repository Integrator  
**To:** Chat 8 — Deputy Orchestrator 2 / Final Reviewer  
**Date:** 2026-09-30

## Review target

Final-review only this exact candidate:

- branch: `integration/pass-4-candidate`
- candidate SHA: `05f999e1cc24307cfb4842d19bc5d42a1f1c9721`
- candidate tree: `fa751dce49166023741324c338f1dd587b24cc49`
- candidate parent/base: `11975decc69caf80952942c58377f9d896d70303`
- PR: `#38 — Round 4 — Deputy 1 integration candidate`

Do not substitute newer worker branches or later worker-local passes for these accepted Round-4 cuts.

## Required source documents

Read from `main`:

1. `chat_6_orchestrator/ROUND_4_STAGE1_FINAL_REVIEW_2026-09-30.md`
2. `chat_6_orchestrator/ROUND_4_REPLAY_MANIFEST_2026-09-30.md`
3. `chat_6_orchestrator/ROUND_4_STAGE2_REVIEW_2026-09-30.md`
4. `chat_6_orchestrator/ORCHESTRATION_STATE.md`
5. `chat_6_orchestrator/SLICE_STATUS.md`

## Frozen provenance to re-check

- Chat 1: `chat-1/pass-4` @ `a7d607f8cdd281749ae40529de15c2d84dfda78e`
- Chat 2: `chat-2/pass-6` @ `539d58567046fd29ccf2d42b629227ffe8da6546`
- Chat 3: `chat-3/pass-8` @ `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`
- Chat 4: `chat-4/pass-7` @ `61f37a4dd46921b7fe9145bcbe5242bc3f6417b3`
- Chat 5: `chat-5/pass-8` @ `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`

## CI to independently verify

Candidate push run:

`36728546973` — expected `SUCCESS`

Candidate PR run:

`36728980497` — expected `SUCCESS`

The PR run must show all of the following actually executed and `SUCCESS`:

- Contracts / canonical fixtures
- Chat 1 / Capture
- Chat 2 / Measurement
- Chat 3 / Geometry
- Chat 4 / Generic CAD gate
- Chat 5 / Lifecycle
- Integration / Chat 1 -> Chat 2
- Integration / Chat 2 -> Chat 3
- Integration / Chat 3 -> Chat 4
- Integration / Chat 4 -> Chat 5
- Integration / Round 3 golden path

## Candidate scope expectation

The exact candidate should be one commit ahead of base `11975de...` and should modify only accepted Chat 1–5 worker-owned replay content.

Shared/protected surfaces must remain the current-main versions:

- `.github/workflows/**`
- `core/contracts/**`
- root canonical fixtures
- root `tests/integration/**`
- worker `ORCHESTRATOR_DIRECTIVE.md`
- worker `ORCHESTRATOR_HANDOFF.md`
- Chat-6 and Chat-8 orchestration files

## Known process defect

Deputy 1 was instructed to create:

- `ROUND_4_DEPUTY1_AUDIT.md`
- `ROUND_4_INTEGRATION_CANDIDATE_REPORT.md`

Those files are not present in the repository/candidate at the time of Chat-6 Stage-2 review.

Do not claim they exist.

PR #38 contains the Deputy-1 candidate summary, and Chat 6 independently verified provenance/tree/CI in `ROUND_4_STAGE2_REVIEW_2026-09-30.md`. Treat the missing two files as a documented process defect, not as evidence of a code failure unless your independent review finds substantive missing proof.

## External runtime exception

Must remain:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

Do not infer real-host PASS from generic CAD/test-double CI.

## Final reviewer authority

Chat 8 must issue one of:

```text
FINAL_REVIEW_ACCEPT_EXACT_SHA
FINAL_REVIEW_FIX_REQUIRED
```

If accepted, the decision must name exact candidate SHA `05f999e1cc24307cfb4842d19bc5d42a1f1c9721` and exact base/main SHA used for the review.

Do not merge to `main` as part of Final Review unless the Chat-6 workflow explicitly delegates that action after the independent verdict.
