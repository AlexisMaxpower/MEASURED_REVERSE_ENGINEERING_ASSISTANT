# MREA — Round 4 Final Review Handoff V2

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Date:** 2026-09-30  
**Supersedes for final-candidate identity:** `ROUND_4_FINAL_REVIEW_HANDOFF_2026-09-30.md`

## Why V2 exists

Chat 6 independently accepted the Deputy-1 candidate `05f999e1cc24307cfb4842d19bc5d42a1f1c9721` technically and recorded Stage-2 evidence on `main`.

Those Stage-2 evidence commits necessarily advanced `main` after the candidate had been built from `11975decc69caf80952942c58377f9d896d70303`.

Therefore `05f999e1...` remains valid Stage-2 evidence, but it must **not** be presented as the final-review candidate based on the latest `main`.

## Final-review rebuild rule

After the Chat-6 Stage-2 documentation set is frozen on `main`, Chat 6 must rebuild `integration/pass-4-candidate` exactly once from that final documentation HEAD using the same verified worker-owned replay trees.

No additional `main` write is allowed after that rebuild until Chat 8 completes Final Review.

The rebuilt candidate must:

1. have the frozen documentation `main` HEAD as its only parent;
2. contain the same accepted worker-owned Round-4 replay surfaces already verified against `ROUND_4_REPLAY_MANIFEST_2026-09-30.md`;
3. preserve current shared/protected infrastructure;
4. obtain a new full candidate CI run with all required jobs actually executed + `SUCCESS`.

## Exact final-candidate source of truth

To avoid another circular `main` advance, the **exact rebuilt candidate SHA and new CI run ID will not be written back to `main`**.

They will be recorded by Chat 6 as the latest authoritative handoff comment on PR #38 after the rebuilt candidate CI completes.

Chat 8 must therefore use:

- this V2 handoff from `main` for policy;
- the latest Chat-6 handoff comment on PR #38 for exact final candidate SHA/base SHA/CI run.

Any older PR description or older handoff naming `05f999e1...` as final-review target is superseded if the PR head has moved after this V2 handoff.

## Stable provenance

The accepted Round-4 worker cuts remain:

- Chat 1 `chat-1/pass-4` @ `a7d607f8cdd281749ae40529de15c2d84dfda78e`
- Chat 2 `chat-2/pass-6` @ `539d58567046fd29ccf2d42b629227ffe8da6546`
- Chat 3 `chat-3/pass-8` @ `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`
- Chat 4 `chat-4/pass-7` @ `61f37a4dd46921b7fe9145bcbe5242bc3f6417b3`
- Chat 5 `chat-5/pass-8` @ `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`

The Deputy-1 documentation defect also remains recorded: the specifically requested files `ROUND_4_DEPUTY1_AUDIT.md` and `ROUND_4_INTEGRATION_CANDIDATE_REPORT.md` were not found and must not be claimed to exist.

## External runtime truth

Unchanged:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Merge policy

```text
CHAT8_FINAL_REVIEW_REQUIRED = TRUE
MERGE_TO_MAIN_AUTHORIZED = FALSE
```

Chat 8 must independently verify the rebuilt exact SHA and issue the final exact-SHA decision before any merge.
