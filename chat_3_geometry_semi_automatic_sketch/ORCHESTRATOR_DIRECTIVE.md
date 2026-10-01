# ORCHESTRATOR DIRECTIVE — Chat 3

**Revision:** `OD-2026-09-30-004`  
**Owner:** Chat 6  
**Central round:** 4  
**Selected worker cut:** `chat-3/pass-8` @ `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`

## Accepted central baseline

Round 3 is closed. Chat 3 Pass 3 is accepted in `main`.

Round-4 plan:

`chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`

## Selected cumulative input

Chat 6 selects the frozen `chat-3/pass-8` cumulative branch for Round-4 Stage-1 review.

The selected worker stack advances geometry/constraint behavior through deterministic constraint satisfaction and residual-aware confidence.

## Known shared-baseline drift

The Pass-8 handoff truthfully reports inherited old Chat-6-owned integration-test code that reads:

`cad_verification_report["dimensions"]`

Current accepted `main` uses canonical:

`cad_verification_report["items"]`

This is shared-baseline drift, not permission for Chat 3 to patch shared infrastructure.

## OD-004 task

No new normal worker implementation is requested now.

Keep `chat-3/pass-8` frozen unless Chat 6 returns explicit `FIX_REQUIRED`.

Chat 6 will review and replay only accepted Chat-3-owned changes onto current `main`. Stale shared CI/integration files from worker ancestry are excluded.

## Truth invariants under review

- physical measurements remain stronger evidence than inferred geometry/relations;
- geometry extraction must not modify verified measurement values;
- normalization remains in Chat 3, not Chat 2;
- constraint candidates are not silently promoted when unsatisfied or below confidence threshold;
- unsupported/ambiguous constraints remain explicit `unresolved`;
- residual/confidence logic may weaken inferred confidence but must never strengthen upstream evidence;
- no CAD-vendor logic enters Chat 3.

## Round-4 boundary focus

Chat3->Chat4 must prove:

```text
constraint candidate
-> satisfaction residual
-> residual-aware confidence
-> canonical constraint OR explicit unresolved
-> generic/vendor CAD transfer without truth strengthening
```

## Required gates

During central review/replay the selected cut must keep green:

- `Chat 3 / Geometry`;
- `Integration / Chat 2 -> Chat 3`;
- `Integration / Chat 3 -> Chat 4` using the current-main canonical shared test;
- canonical contracts/fixtures.

## Do not

- backport the obsolete shared `dimensions` lookup;
- modify Chat-6-owned shared integration tests;
- push Pass 9 work onto the selected frozen cut;
- change canonical contracts without approved CR;
- merge directly to `main`.

## Current state

```text
CHAT_3_PASS_8 = FROZEN_SELECTED_FOR_ROUND4_STAGE1
KNOWN_SHARED_BASELINE_DRIFT = TRUE
CENTRAL_REPLAY_REQUIRED = TRUE
ROUND_4_STAGE1_ACCEPTANCE = PENDING_CHAT6
```
