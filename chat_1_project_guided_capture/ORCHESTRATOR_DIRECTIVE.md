# ORCHESTRATOR DIRECTIVE — Chat 1
**Revision:** OD-2026-09-29-003  
**Owner:** Chat 6  
**Pass:** 3  
**Branch:** `chat-1/pass-3`

Read before coding.

## Accepted baseline
Pass 2 is `ACCEPTED`. Perspective normalization/rectification is integrated in `main`. Clean reference evidence remains immutable. The real repository-level `Chat 1 -> Chat 2` integration gate is now canonical CI.

## Pass 3 priority
Implement the first useful **guided capture quality baseline**.

Required:
- deterministic capture-quality analysis for blur/focus;
- exposure clipping / underexposure-overexposure signal;
- glare/highlight proxy;
- framing/working-area quality where feasible with current architecture;
- reuse calibration-marker visibility/quality where appropriate;
- explicit internal acceptance result such as ACCEPT/WARN/REJECT with machine-readable reasons;
- no conversion of image-quality inference into metric truth;
- deterministic good/bad fixtures and tests;
- keep CapturePackage v1 compatible unless Chat 6 approves a Change Request.

## Canonical integration gates
Your pass must keep green:
- `Chat 1 / Capture`;
- `Integration / Chat 1 -> Chat 2`;
- shared contract checks.

## Do not
- implement measurement semantics, OCR or caliper interpretation;
- move geometry ownership into Capture;
- modify Chat-6-owned CI/shared integration tests;
- modify `core/contracts` without approved CR;
- commit directly to `main`.

## Process
Work only in `chat-1/pass-3`.

Finish by publishing `ORCHESTRATOR_HANDOFF.md`. **Handoff freezes the branch.** After handoff do not push any code or documentation, even to record later CI evidence, until Chat 6 explicitly returns `FIX_REQUIRED`.

See `chat_6_orchestrator/PASS_3_PLAN_2026-09-29.md` and `DEVELOPMENT_WORKFLOW.md`.
