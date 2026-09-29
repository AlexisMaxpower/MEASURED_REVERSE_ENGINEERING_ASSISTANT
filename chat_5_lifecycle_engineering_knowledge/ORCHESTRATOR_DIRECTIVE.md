# ORCHESTRATOR DIRECTIVE — Chat 5
**Revision:** OD-2026-09-29-003  
**Owner:** Chat 6  
**Pass:** 3  
**Branch:** `chat-5/pass-3`

## Accepted baseline
Pass 2 is `ACCEPTED`. CAD verification now controls manufacturing eligibility and the real `Chat 4 -> Chat 5` integration gate is green on accepted `main`.

## Pass 3 priority
Extend lifecycle to the **physical manufactured part instance** and its real-world use.

Required:
- introduce physical part instance identity tied to revision and manufacturing record;
- deterministic lifecycle transitions for manufactured, installed, tested, active/in-service, failed, removed and replaced/superseded where appropriate;
- installation must identify equipment/position or equivalent location context;
- preserve failure evidence and relationship to the exact physical instance and revision;
- explicitly reject invalid transitions;
- keep CAD verification/manufacturing eligibility invariant intact;
- add deterministic state-transition and timeline tests;
- keep facts structured; no AI analysis in this pass.

## Canonical integration gates
Your pass must keep green:
- `Chat 5 / Lifecycle`;
- `Integration / Chat 4 -> Chat 5`;
- shared contract checks.

## Do not
- import SOLIDWORKS-specific types;
- bypass failed/unverified CAD eligibility;
- add AI conclusions before physical lifecycle facts are stable;
- modify Chat-6-owned CI/shared integration tests;
- change canonical shared contracts without approved CR;
- commit directly to `main`.

## Process
Work only in `chat-5/pass-3`.

Finish with `ORCHESTRATOR_HANDOFF.md`. **Handoff freezes the branch.** No post-handoff commits until Chat 6 explicitly returns `FIX_REQUIRED`.

See `chat_6_orchestrator/PASS_3_PLAN_2026-09-29.md` and `DEVELOPMENT_WORKFLOW.md`.
