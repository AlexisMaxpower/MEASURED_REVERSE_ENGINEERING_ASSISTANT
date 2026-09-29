# ORCHESTRATOR DIRECTIVE — Chat 2
**Revision:** OD-2026-09-29-003  
**Owner:** Chat 6  
**Pass:** 3  
**Branch:** `chat-2/pass-3`

## Accepted baseline
Pass 2 is `ACCEPTED`. Raw `IMAGE_PX` anchors/evidence semantics are integrated and the real `Chat 2 -> Chat 3` gate is green. `Chat 1 -> Chat 2` is now also an automated repository boundary gate.

## Pass 3 priority
Implement the **hands-free measurement domain/application baseline** without tying correctness to a specific speech/OCR vendor.

Required:
- provider-independent command parser/state machine for measurement trigger, value candidate, confirm, reject/correct;
- support command intent equivalent to `замер` and `замер 42,18`, including deterministic numeric normalization;
- voice/OCR/device values enter as candidates, not automatically verified facts;
- preserve manual entry as authoritative fallback;
- explicit candidate -> confirmation -> verified transition;
- preserve evidence frame, reference frame, view and provenance;
- keep raw image anchors in `IMAGE_PX`;
- deterministic tests for valid, ambiguous and invalid commands/transitions.

## Canonical integration gates
Your pass must keep green:
- `Chat 2 / Measurement`;
- `Integration / Chat 1 -> Chat 2`;
- `Integration / Chat 2 -> Chat 3`;
- shared contract checks.

## Do not
- implement speech recognition engine from scratch;
- pre-normalize geometry to satisfy Chat 3;
- move geometry matching into Chat 2;
- silently verify OCR/voice candidates;
- modify Chat-6-owned CI/shared integration tests;
- change canonical contracts without approved CR;
- commit directly to `main`.

## Process
Work only in `chat-2/pass-3`.

Finish with `ORCHESTRATOR_HANDOFF.md`. **Handoff freezes the branch.** No post-handoff commits until Chat 6 explicitly returns `FIX_REQUIRED`.

See `chat_6_orchestrator/PASS_3_PLAN_2026-09-29.md` and `DEVELOPMENT_WORKFLOW.md`.
