# ORCHESTRATOR DIRECTIVE — Chat 2

**Revision:** `OD-2026-09-30-004`  
**Owner:** Chat 6  
**Central round:** 4  
**Selected worker cut:** `chat-2/pass-6` @ `539d58567046fd29ccf2d42b629227ffe8da6546`

## Accepted central baseline

Round 3 is closed. Chat 2 Pass 3 is accepted in `main`.

Round-4 plan:

`chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`

## Selected cumulative input

Chat 6 selects the existing frozen `chat-2/pass-6` branch as the cumulative Chat-2 input for Round-4 Stage 1.

This cumulative cut contains worker Pass 4 -> Pass 5 -> Pass 6:

- measurement-type unit semantics;
- unit-neutral uncertainty;
- canonical 1..3 anchor cardinality.

The Pass-6 handoff is treated as the freeze point pending independent Chat-6 review.

## OD-004 task

No new normal worker implementation is requested now.

Keep `chat-2/pass-6` frozen unless Chat 6 returns an explicit `FIX_REQUIRED`.

Chat 6 will independently review and replay accepted Chat-2-owned changes onto the current shared baseline rather than merging worker history wholesale.

## Required truth invariants under review

- raw measurement anchors remain `IMAGE_PX` in Chat 2;
- `ANGLE` uses canonical `deg`;
- length-like measurements use canonical `mm`;
- uncertainty is expressed in the measurement's own unit;
- one, two and three canonical anchors remain ordered and provenance-preserving;
- invalid anchor combinations fail closed;
- voice/OCR/device candidates remain unverified until explicit confirmation;
- verified physical measurement values are not modified by downstream geometry/AI.

## Round-4 boundary focus

Chat2->Chat3 must prove:

```text
1/2/3 raw IMAGE_PX anchors
+ mm/deg semantics
+ unit-neutral uncertainty
-> downstream normalization/binding
```

A valid upstream package must either be supported downstream or rejected explicitly. Silent anchor rewriting or unit coercion is forbidden.

## Required gates

During central review/replay the selected cut must keep green:

- `Chat 2 / Measurement`;
- `Integration / Chat 1 -> Chat 2`;
- `Integration / Chat 2 -> Chat 3`;
- canonical contracts/fixtures.

## Do not

- push Pass 7 work onto the frozen selected cut;
- modify shared integration tests to hide downstream incompatibility;
- move normalization into Chat 2;
- change canonical contracts without approved CR;
- merge directly to `main`.

## Current state

```text
CHAT_2_PASS_6 = FROZEN_SELECTED_FOR_ROUND4_STAGE1
ROUND_4_STAGE1_ACCEPTANCE = PENDING_CHAT6
```
