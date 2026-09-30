# ORCHESTRATOR DIRECTIVE — Chat 4

**Revision:** `OD-2026-09-30-004`  
**Owner:** Chat 6  
**Central round:** 4  
**Worker target branch:** `chat-4/pass-7`

## Accepted central baseline

Round 3 is closed. Chat 4 Pass 3 is accepted for software integration on `main`.

The generic/runtime-evidence path is accepted. Real Windows 11 + installed SOLIDWORKS 2026 execution remains explicitly `UNVERIFIED`.

Round-4 plan:

`chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`

## Observed later state

Observed branch head before this directive delivery:

`d9633e3b8e95158d359e502e9797d4876384cd09`

Observed later work includes broader SOLIDWORKS vendor capability including fail-closed ANGLE dimensions.

Problem:

`chat-4/pass-7` still contains an `ORCHESTRATOR_HANDOFF.md` that identifies Pass 3.

Therefore the current Pass-7 branch is not yet a protocol-valid frozen Stage-1 input.

## OD-004 task

Do **not** begin Pass 8.

Finish the existing cumulative Chat-4 work through Pass 7 as one reviewable worker cut:

1. inspect current `chat-4/pass-7` against accepted Round-3 main and current canonical contracts;
2. correct only defects required for a truthful cumulative Pass-7 handoff;
3. run available Chat-4 generic and adjacent boundary gates;
4. publish a current Pass-7 `ORCHESTRATOR_HANDOFF.md` recording:
   - exact branch;
   - exact implementation/pre-handoff SHA;
   - cumulative scope since accepted Pass 3;
   - exact CI run IDs/results;
   - changed files / ownership statement;
   - unsupported vendor cases;
   - `REAL_HOST` truth;
   - production C# build truth;
   - explicit branch freeze;
5. freeze `chat-4/pass-7` after the handoff commit.

## Required truth invariants

- canonical/Primary verification semantics remain vendor-neutral;
- SOLIDWORKS types stay behind the adapter/process boundary;
- unsupported geometry/dimensions/constraints fail explicitly;
- vendor success does not imply canonical `VERIFIED` without Primary read-back verification;
- generic CAD CI must not require installed SOLIDWORKS;
- real-host success may be claimed only from an actual controlled Windows 11 x64 + SOLIDWORKS 2026 x64 run.

## Required gates

Keep green where executable in repository CI:

- `Chat 4 / Generic CAD gate`;
- `Integration / Chat 3 -> Chat 4`;
- `Integration / Chat 4 -> Chat 5`;
- canonical contracts/fixtures.

## Environment truth

Until actual controlled-host evidence exists:

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
NATIVE SLDPRT GENERATION/READBACK = UNVERIFIED
```

Static/unit/test-double evidence cannot promote those states.

## Do not

- start Pass 8;
- modify Chat-6-owned CI/shared integration tests;
- change canonical contracts without approved CR;
- weaken read-back verification;
- merge directly to `main`;
- claim Stage-1 acceptance before Chat 6 review.

## Completion state

Expected final worker state:

```text
CHAT_4_PASS_7 = HANDOFF_PUBLISHED_AND_FROZEN
REAL_HOST = UNVERIFIED unless actual controlled-host evidence exists
ROUND_4_STAGE1_ACCEPTANCE = PENDING_CHAT6
```
