# ORCHESTRATOR DIRECTIVE — Chat 4
**Revision:** OD-2026-09-29-003  
**Owner:** Chat 6  
**Pass:** 3  
**Branch:** `chat-4/pass-3`

## Accepted baseline
Pass 2 is `ACCEPTED_WITH_RUNTIME_GATE`. Generic CAD transfer/verification and the SOLIDWORKS 2026 agent architecture are integrated. Real Windows 11 + installed SOLIDWORKS 2026 execution remains explicitly `UNVERIFIED`.

A real repository-level `Chat 3 -> Chat 4` gate and the existing `Chat 4 -> Chat 5` gate are canonical CI.

## Pass 3 priority
Make the SOLIDWORKS host path **ready for controlled real-host validation** without weakening the generic gate.

Required:
- preserve current generic/test-double CAD behavior and canonical semantics;
- fail-closed preflight checks/diagnostics for Windows/x64, required agent prerequisites, SOLIDWORKS availability/version where feasible, interop availability and writable artifact path;
- machine-readable failure reasons and clear exit codes;
- make golden smoke execution one-command or minimal-command and deterministic;
- runtime evidence format must be able to record SOLIDWORKS version, input SketchPackage identity, native artifact identity/hash, read-back dimensions and verification result;
- do not claim real runtime VERIFIED until an actual installed SOLIDWORKS run supplies evidence;
- POINT/ARC/additional constraint support is secondary and must not weaken host-readiness or fail-closed behavior.

## Canonical integration gates
Your pass must keep green:
- `Chat 4 / Generic CAD gate`;
- `Integration / Chat 3 -> Chat 4`;
- `Integration / Chat 4 -> Chat 5`;
- shared contract checks.

## Environment gate
A real Windows 11 + SOLIDWORKS 2026 host run may remain `UNVERIFIED` during Pass 3 if no controlled host is connected. Do not fake or infer success.

## Do not
- leak SOLIDWORKS types into canonical contracts;
- weaken read-back verification;
- make generic CI require installed SOLIDWORKS;
- modify Chat-6-owned CI/shared integration tests;
- commit directly to `main`.

## Process
Work only in `chat-4/pass-3`.

Finish with `ORCHESTRATOR_HANDOFF.md`. **Handoff freezes the branch.** No post-handoff commits until Chat 6 explicitly returns `FIX_REQUIRED`.

See `chat_6_orchestrator/PASS_3_PLAN_2026-09-29.md`, `ADR_001_SOLIDWORKS_2026_CAD_AGENT.md` and `DEVELOPMENT_WORKFLOW.md`.
