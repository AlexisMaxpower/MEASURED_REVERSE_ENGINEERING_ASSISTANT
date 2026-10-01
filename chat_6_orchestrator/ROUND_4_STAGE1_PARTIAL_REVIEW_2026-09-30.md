# MREA — Round 4 Stage 1 Partial Review

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive:** `OD-2026-09-30-004`  
**Date:** 2026-09-30  
**Status:** `STAGE1_PARTIAL_REVIEW_COMPLETE / WAITING_FOR_CHAT1_CHAT4_HANDOFF`

## Scope of this review

This is a real Stage-1 review of worker cuts that already have frozen handoffs. It does not accept or merge any worker branch into `main`.

Reviewed now:

- Chat 2 cumulative Pass 6;
- Chat 3 cumulative Pass 8;
- Chat 5 cumulative Pass 8.

Not yet reviewable as frozen current-pass inputs:

- Chat 1 Pass 4 — current branch handoff still describes Pass 3;
- Chat 4 Pass 7 — current branch handoff still describes Pass 3.

Therefore Round-4 Stage 1 cannot yet be declared complete.

## Evidence hierarchy used

Review order:

```text
actual repository/branch state
> actual diff / branch ancestry
> actual GitHub Actions results
> canonical contracts/current main
> worker handoff claims
```

No worker PASS statement is accepted without GitHub evidence.

---

# Chat 2 — cumulative Pass 6

## Selected cut

`chat-2/pass-6` @ `539d58567046fd29ccf2d42b629227ffe8da6546`

This is a cumulative worker cut containing Pass 4 -> Pass 5 -> Pass 6 functionality:

- measurement type registry / unit semantics;
- unit-neutral uncertainty;
- canonical 1..3 anchor cardinality.

## Branch ancestry finding

Direct commit comparison against the old Pass-3 worker head is **diverged**, not a clean linear continuation. The branch carries unrelated/shared historical state from its old base.

Therefore:

```text
BLIND MERGE = FORBIDDEN
WHOLE-TREE REPLACEMENT = FORBIDDEN
FILE-LEVEL CHAT-2-OWNED REPLAY = REQUIRED
```

The review does not interpret the large cross-repository compare as Chat-2 ownership. Only Chat-2-owned cumulative deltas are candidates for replay.

## CI evidence

Pass-6 implementation run:

- run `36651166396`;
- head SHA `b5f7a85c66a0c72aa41edd1b045fa5a9f474b9e7`;
- overall `SUCCESS`.

Actually observed `SUCCESS` on that run:

- `Contracts / canonical fixtures`;
- `Chat 2 / Measurement`;
- `Integration / Chat 1 -> Chat 2`;
- `Integration / Chat 2 -> Chat 3`;
- other slice jobs also completed successfully.

Unrelated downstream boundary/golden jobs were conditionally `skipped`; they are not counted as evidence for those boundaries.

The final handoff commit `539d585...` also has a completed `MREA CI` run `36652290223` with overall `SUCCESS`.

## Truth-boundary finding

The selected Chat-2 cut is architecturally consistent with current v1 truth ownership provided central replay verifies:

- raw anchors remain `IMAGE_PX`;
- `ANGLE` remains `deg`;
- length types remain `mm`;
- uncertainty is unit-neutral in the sense of using the measurement's own unit;
- 1..3 anchor order/provenance is preserved;
- downstream code does not silently force all measurements back to two anchors.

## Chat-2 Stage-1 verdict

```text
PROVISIONALLY_ACCEPTED_FOR_FILE_LEVEL_REPLAY
```

Acceptance is not final until the replayed current-main state passes central Round-4 boundary/golden CI.

---

# Chat 3 — cumulative Pass 8

## Selected cut

`chat-3/pass-8` @ `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`

Selected functionality advances geometry/constraint processing through residual-aware confidence.

## Known baseline drift independently confirmed

Worker implementation run:

- run `36651103396`;
- head SHA `1a6b58e6e87786b8e67e6f8525ece98e588dfad3`;
- overall conclusion: **FAILURE**.

Observed jobs:

- `Contracts / canonical fixtures` — `SUCCESS`;
- `Chat 3 / Geometry` — `SUCCESS`;
- `Chat 2 / Measurement` — `SUCCESS`;
- `Chat 4 / Generic CAD gate` — `SUCCESS`;
- `Integration / Chat 2 -> Chat 3` — `SUCCESS`;
- `Integration / Chat 3 -> Chat 4` — **FAILURE**.

The worker handoff identifies the failure as inherited shared-baseline drift: the old branch copy of the shared test reads `cad_verification_report["dimensions"]`, whereas current accepted `main` uses canonical `items`.

Chat 3 did not patch the Chat-6-owned test, which is the correct ownership behavior.

## Decision on the red run

The overall red workflow is not hidden or relabeled as green.

It means the branch itself is **not directly mergeable/certifiable**.

However, because:

1. current `main` already contains the corrected canonical shared boundary test;
2. Chat-3-owned geometry tests pass;
3. Chat2->Chat3 passes;
4. the failure occurs in stale shared ancestry outside Chat-3 ownership;

Chat 6 permits only a controlled file-level replay of Chat-3-owned changes onto current `main`, followed by mandatory rerun of current-main Chat3->Chat4.

## Truth-boundary finding

Central replay must prove:

- constraint residual/confidence cannot strengthen physical measurement evidence;
- unsatisfied/low-confidence constraints remain explicit unresolved;
- no inferred relation modifies verified geometry/measurement truth;
- CAD receives only canonical promoted constraints/unresolved state.

## Chat-3 Stage-1 verdict

```text
PROVISIONALLY_ACCEPTED_WITH_CURRENT_MAIN_REPLAY_REQUIRED
```

Mandatory before Stage 1 final acceptance:

```text
CURRENT_MAIN_REPLAY
+ Chat 3 / Geometry = SUCCESS
+ Chat 2 -> Chat 3 = SUCCESS
+ Chat 3 -> Chat 4 = SUCCESS
```

No direct merge of `chat-3/pass-8` is authorized.

---

# Chat 5 — cumulative Pass 8

## Selected cut

`chat-5/pass-8` @ `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`

The selected cumulative stack advances lifecycle/read-only/engineering-knowledge behavior through snapshot-bound pagination.

## CI evidence

Pass-8 pre-handoff run:

- run `36651237369`;
- head SHA `1b45f9a2b815ff4a150dd9a49d21dde4abdde9df`;
- overall `SUCCESS`.

Actually observed `SUCCESS`:

- `Chat 5 / Lifecycle`;
- `Contracts / canonical fixtures`;
- `Chat 4 / Generic CAD gate`;
- `Integration / Chat 4 -> Chat 5`;
- all five slice jobs on the run.

Unrelated boundary jobs were conditionally skipped and are not counted as evidence for those paths.

## Truth-boundary finding

The selected Chat-5 cut is acceptable for replay only if central verification confirms:

- manufacturing eligibility remains derived from canonical CAD verification;
- vendor-only success cannot bypass `MISMATCH`/`UNVERIFIED`;
- lifecycle history remains append/fact oriented and fail closed;
- read-only/knowledge projections do not upgrade or reinterpret factual evidence;
- cursor/query pagination remains snapshot/filter bound.

## Chat-5 Stage-1 verdict

```text
PROVISIONALLY_ACCEPTED_FOR_FILE_LEVEL_REPLAY
```

Acceptance remains conditional on current-main replay and central Chat4->Chat5 / golden CI.

---

# Chat 1 / Chat 4 blocking state

## Chat 1

Target:

`chat-1/pass-4` @ observed `beed09508c8cba294b1e78d7b6b7f3226f72d734`

Current handoff still names Pass 3.

Verdict:

```text
FIX_REQUIRED_HANDOFF_ONLY
```

OD-004 already instructs Chat 1 to publish a truthful Pass-4 handoff and freeze without starting another feature pass.

## Chat 4

Target:

`chat-4/pass-7` @ observed `d9633e3b8e95158d359e502e9797d4876384cd09`

Current handoff still names Pass 3.

Verdict:

```text
FIX_REQUIRED_HANDOFF_ONLY
```

OD-004 already instructs Chat 4 to publish a truthful cumulative Pass-7 handoff/freeze and preserve:

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

unless actual controlled-host evidence exists.

---

# Stage-1 partial conclusion

```text
CHAT_1 = FIX_REQUIRED_HANDOFF_ONLY
CHAT_2 = PROVISIONALLY_ACCEPTED_FOR_FILE_LEVEL_REPLAY
CHAT_3 = PROVISIONALLY_ACCEPTED_WITH_CURRENT_MAIN_REPLAY_REQUIRED
CHAT_4 = FIX_REQUIRED_HANDOFF_ONLY
CHAT_5 = PROVISIONALLY_ACCEPTED_FOR_FILE_LEVEL_REPLAY

ROUND_4_STAGE1_COMPLETE = FALSE
ROUND_4_STAGE1_BLOCKER = CHAT_1_AND_CHAT_4_CURRENT_HANDOFFS
INTEGRATION_PASS_4_CANDIDATE_AUTHORIZED = FALSE
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
```

Next Chat-6 action after the two required handoffs land:

1. independently review final Chat-1 and Chat-4 worker cuts;
2. construct exact file-level replay manifest for all provisionally accepted worker deltas;
3. run the replayed state against current-main CI/boundary tests;
4. publish final Round-4 Stage-1 review and merge/replay plan;
5. only then hand to Chat 7 for `integration/pass-4-candidate`.
