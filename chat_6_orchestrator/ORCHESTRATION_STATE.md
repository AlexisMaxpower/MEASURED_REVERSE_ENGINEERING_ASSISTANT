# MREA Orchestration State

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive revision:** `OD-2026-09-30-004`  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** Round 3 CLOSED — Round 4 Stage 1 BLOCKED on Chat 1 / Chat 4 current-pass handoffs

## Source-of-truth hierarchy

1. Current accepted repository state on `main`.
2. Canonical shared contracts in `core/contracts/`.
3. Canonical fixtures and Chat-6 integration tests under `tests/`.
4. Chat 6 ADR/review/workflow/CI documents and active directives.
5. Product SSOT v0.1 plus orchestration addendum.
6. Slice-local documentation.

If slice-local documentation conflicts with canonical contracts or an active Chat 6 directive, canonical/Chat-6 truth wins.

## Round 3 closure

Final accepted Round-3 software baseline before Round-4 planning commits:

`bffc1dec2fe63c12b69a50c4bf348ef7df4cf662`

Accepted tree:

`435dda140d3980256ca32c42bd07d81b15c4328c`

Post-merge MREA CI:

`36651010221` — `SUCCESS`

Round-3 golden path: `SUCCESS`.

Overall verdict: **ROUND 3 SOFTWARE INTEGRATION CLOSED / VERIFIED**.

External vendor truth remains separate:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Round 4 purpose

Round 4 is **Backlog Reconciliation & Cross-Slice Truth Hardening**.

Primary documents:

- `chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`;
- `chat_6_orchestrator/ROUND_4_WORKER_INTAKE_2026-09-30.md`;
- `chat_6_orchestrator/ROUND_4_STAGE0_STATE_RESET.md`;
- `chat_6_orchestrator/ROUND_4_STAGE1_PARTIAL_REVIEW_2026-09-30.md`;
- `chat_6_orchestrator/ROUND_4_STAGE1_RECHECK_2026-09-30.md`.

## Round 4 selected worker cuts

```text
Chat 1  chat-1/pass-4
        implementation before Chat-6 directive delivery: 3da301bc3cfeb261d5bab4145d094a4429190e5b
        current checked branch head: f033c6b24d2d85be52d0255cb12c897a496dd1da
        OD-004 DELIVERED
        current ORCHESTRATOR_HANDOFF still describes Pass 3
        -> FIX_REQUIRED_HANDOFF_ONLY

Chat 2  chat-2/pass-6 @ 539d58567046fd29ccf2d42b629227ffe8da6546
        frozen handoff present
        -> PROVISIONALLY_ACCEPTED_FOR_FILE_LEVEL_REPLAY

Chat 3  chat-3/pass-8 @ d786e1d49b5c8f2837a3ce936f7f1c0d93336d49
        frozen handoff present
        known stale shared-baseline drift
        -> PROVISIONALLY_ACCEPTED_WITH_CURRENT_MAIN_REPLAY_REQUIRED

Chat 4  chat-4/pass-7
        implementation before Chat-6 directive delivery: d9633e3b8e95158d359e502e9797d4876384cd09
        current checked branch head: 2b4b34fe4d5053b189bc65172e04150eda4e29b7
        OD-004 DELIVERED
        current ORCHESTRATOR_HANDOFF still describes Pass 3
        -> FIX_REQUIRED_HANDOFF_ONLY

Chat 5  chat-5/pass-8 @ 82e2203aaeb69ee1fe9f89fd42d0aea451b8690f
        frozen handoff present
        -> PROVISIONALLY_ACCEPTED_FOR_FILE_LEVEL_REPLAY
```

Worker-local pass numbers are not central-round numbers.

## Directive delivery correction

Chat 6 independently found that the active Chat-1 and Chat-4 worker branches still contained OD-003 even though `main` contained OD-004. This was a Chat-6 coordination-delivery defect.

Correction pushed directly to the active branches, changing only the Chat-6-owned directive file:

- Chat 1 directive delivery commit `f033c6b24d2d85be52d0255cb12c897a496dd1da`;
  - CI `36661241393` — SUCCESS;
  - Contracts — SUCCESS;
  - Chat 1 / Capture — SUCCESS;
  - Chat 1 -> Chat 2 — SUCCESS.
- Chat 4 directive delivery commit `2b4b34fe4d5053b189bc65172e04150eda4e29b7`;
  - CI `36661262220` — SUCCESS;
  - Contracts — SUCCESS;
  - Chat 4 / Generic CAD gate — SUCCESS;
  - Chat 3 -> Chat 4 — SUCCESS;
  - Chat 4 -> Chat 5 — SUCCESS.

These commits do not constitute worker handoffs and do not accept the worker cuts.

## Round 4 integration policy

Future Round-4 candidate construction must start from the then-current accepted `main` and perform file-level replay of accepted worker-owned changes.

Forbidden:

- blind worker-history merge;
- whole-worker-directory replacement;
- importing stale `.github/workflows`, `core/contracts`, canonical fixtures or shared integration tests from worker ancestry;
- overwriting current Chat-6-owned directive files with stale worker copies.

## Round 4 Stage-1 prerequisites

Stage 1 cannot complete until:

1. Chat 1 publishes a truthful Pass-4 handoff/freeze on `chat-1/pass-4` after reading OD-004;
2. Chat 4 publishes a truthful cumulative Pass-7 handoff/freeze on `chat-4/pass-7` after reading OD-004;
3. Chat 6 independently reviews both final handoffs/cuts;
4. Chat 6 constructs the exact file-level replay manifest for all accepted worker deltas;
5. the replayed current-main state passes required slice/boundary/golden verification.

No `integration/pass-4-candidate` is authorized before these conditions are satisfied.

## CI baseline

Canonical workflow: `.github/workflows/ci.yml`.

Policy: `chat_6_orchestrator/CI_POLICY.md`.

Mandatory central evidence remains:

- canonical contracts/fixtures;
- all five slice suites;
- all four real producer-consumer boundary gates;
- complete golden software path;
- post-merge `main` CI.

Worker-local PASS claims are insufficient when GitHub Actions can execute the same gate centrally.

## Shared truth rules

- IDs are opaque non-empty strings; UUIDs are recommended but not required by wire contracts.
- Timestamps are UTC/RFC3339.
- v1 length unit is `mm`; angle unit is `deg`.
- Verified physical measurements are never silently modified by CV/AI.
- Raw measurement anchors remain `IMAGE_PX` until Chat 3 normalization obtains `MAT_XY_MM`.
- CAD transfer verification is numerical transfer verification, not manufacturing tolerance verification.
- Default CAD transfer tolerance remains `1e-6 mm` / `1e-6 deg` unless explicitly changed through accepted architecture/contract process.
- SketchPackage v1 mandatory primitive subset remains POINT, LINE, CIRCLE, ARC.
- Unsupported/ambiguous geometry and constraints remain explicit in `unresolved`.
- Vendor success alone does not authorize manufacturing.
- Lifecycle/knowledge projections must not strengthen failed/unverified CAD or measurement facts.

## SOLIDWORKS runtime gate

Generic CAD logic remains independently testable in GitHub-hosted CI.

Real SOLIDWORKS 2026 COM integration remains a separate environment gate and stays `UNVERIFIED` until a controlled Windows 11 x64 + installed SOLIDWORKS 2026 x64 run produces actual build/startup/artifact/read-back/runtime evidence.

## Change control

No shared contract change is pre-approved for Round 4.

Any backward-incompatible or wire-semantic shared contract change requires a concrete Change Request and Chat-6 decision before implementation/integration.

## Current state machine

```text
ROUND_3_CLOSED
    -> ROUND_4_STAGE0_COMPLETE
    -> ROUND_4_STAGE1_PARTIAL_REVIEW
    -> OD004_DELIVERY_TO_CHAT1_CHAT4_FIXED
    -> WAITING_FOR_CHAT1_CHAT4_CURRENT_HANDOFFS
    -> ROUND_4_STAGE1_COMPLETE = FALSE
    -> INTEGRATION_PASS_4_CANDIDATE_NOT_AUTHORIZED
```
