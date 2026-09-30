# MREA Orchestration State

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive revision:** `OD-2026-09-30-004`  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** Round 3 CLOSED — Round 4 worker intake active

## Source-of-truth hierarchy

1. Current accepted repository state on `main`.
2. Canonical shared contracts in `core/contracts/`.
3. Canonical fixtures and Chat-6 integration tests under `tests/`.
4. Chat 6 ADR/review/workflow/CI documents and active directives.
5. Product SSOT v0.1 plus orchestration addendum.
6. Slice-local documentation.

If slice-local documentation conflicts with canonical contracts or an active Chat 6 directive, the canonical/Chat 6 source wins.

## Round 3 closure

Final accepted Round-3 software baseline before Round-4 planning commits:

`bffc1dec2fe63c12b69a50c4bf348ef7df4cf662`

Accepted tree:

`435dda140d3980256ca32c42bd07d81b15c4328c`

Post-merge MREA CI:

`36651010221` — `SUCCESS`

Round-3 golden path:

`SUCCESS`

Overall verdict:

**ROUND 3 SOFTWARE INTEGRATION CLOSED / VERIFIED**

External vendor truth remains separate:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Accepted slice baseline on main

The current accepted central product baseline contains the frozen Round-3 worker results:

- Chat 1: Pass 3 accepted — guided capture quality baseline;
- Chat 2: Pass 3 accepted — hands-free measurement candidate/confirmation baseline;
- Chat 3: Pass 3 accepted — semi-automatic geometry candidate extraction baseline;
- Chat 4: Pass 3 accepted for software integration — runtime-evidence/host-readiness path, real host still unverified;
- Chat 5: Pass 3 accepted — physical manufactured-part lifecycle baseline.

All five Round-3 slice trees were certified together through Stage 2, Stage 3 and post-merge main CI.

## Current integration status

```text
Chat 1 -> Chat 2    PASS on Round-3 final main
Chat 2 -> Chat 3    PASS on Round-3 final main
Chat 3 -> Chat 4    PASS on Round-3 final main
Chat 4 -> Chat 5    PASS on Round-3 final main
Round-3 golden path PASS on Round-3 final main
```

These results certify the Round-3 baseline, not later Pass-4+ worker backlog.

## Round 4 purpose

Round 4 is:

**Backlog Reconciliation & Cross-Slice Truth Hardening**

Primary documents:

- `chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`;
- `chat_6_orchestrator/ROUND_4_WORKER_INTAKE_2026-09-30.md`;
- `chat_6_orchestrator/ROUND_4_STAGE0_STATE_RESET.md`.

## Round 4 worker intake

Observed later worker branches selected/targeted for Stage 1:

```text
Chat 1  chat-1/pass-4  @ beed09508c8cba294b1e78d7b6b7f3226f72d734
        -> HANDOFF_REQUIRED

Chat 2  chat-2/pass-6  @ 539d58567046fd29ccf2d42b629227ffe8da6546
        -> FROZEN CUMULATIVE CUT SELECTED FOR REVIEW

Chat 3  chat-3/pass-8  @ d786e1d49b5c8f2837a3ce936f7f1c0d93336d49
        -> FROZEN CUMULATIVE CUT SELECTED FOR REVIEW
        -> KNOWN SHARED-BASELINE DRIFT

Chat 4  chat-4/pass-7  @ d9633e3b8e95158d359e502e9797d4876384cd09
        -> HANDOFF_REQUIRED
        -> REAL HOST UNVERIFIED

Chat 5  chat-5/pass-8  @ 82e2203aaeb69ee1fe9f89fd42d0aea451b8690f
        -> FROZEN CUMULATIVE CUT SELECTED FOR REVIEW
```

Worker-local pass numbers are not central-round numbers. The selected cumulative cuts are subject to independent Chat-6 Stage-1 review before any integration candidate is authorized.

## Round 4 integration policy

Future Round-4 candidate construction must start from the then-current accepted `main` and perform file-level replay of accepted worker-owned changes.

Forbidden:

- blind worker-history merge;
- whole-worker-directory replacement;
- importing stale `.github/workflows`, `core/contracts`, canonical fixtures or shared integration tests from worker ancestry;
- overwriting current Chat-6-owned `ORCHESTRATOR_DIRECTIVE.md` files with stale worker copies.

This policy exists because later worker branches were developed against older shared baselines and because whole-directory replacement can regress central orchestration metadata.

## Round 4 Stage-1 prerequisites

Before Stage 1 can complete:

1. Chat 1 must publish a truthful Pass-4 handoff/freeze on `chat-1/pass-4`;
2. Chat 4 must publish a truthful current Pass-7 handoff/freeze on `chat-4/pass-7`;
3. Chat 6 must independently review selected Chat 2/3/5 cumulative cuts;
4. Chat 6 must verify required worker CI and adjacent boundaries;
5. Chat 6 must issue exact Stage-1 verdicts and a file-level replay/merge plan.

No `integration/pass-4-candidate` is authorized before those conditions are satisfied.

## CI baseline

Canonical workflow:

`.github/workflows/ci.yml`

Policy:

`chat_6_orchestrator/CI_POLICY.md`

Mandatory central evidence remains:

- canonical contracts/fixtures;
- all five slice suites;
- all four real producer-consumer boundary gates;
- complete golden software path;
- post-merge `main` CI.

Worker-local PASS claims are insufficient when GitHub Actions can execute the same gate centrally.

## Active architectural decisions

- `ADR_001_SOLIDWORKS_2026_CAD_AGENT.md` defines the SOLIDWORKS adapter environment.
- Per-chat worker branches remain isolated until orchestrator acceptance.
- Publishing a valid current-pass `ORCHESTRATOR_HANDOFF.md` freezes that worker branch.
- Chat 6 owns canonical contracts, fixtures, active worker directives, shared integration tests and orchestration policy.
- Chat 7 owns Stage-2 audit and `integration/pass-N-candidate` construction.
- Chat 8 owns final certification, exact merge decision and round closure.

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

Real SOLIDWORKS 2026 COM integration remains a separate environment gate. It stays `UNVERIFIED` until a controlled Windows 11 x64 + installed SOLIDWORKS 2026 x64 run produces actual build/startup/artifact/read-back/runtime evidence.

## Change control

No shared contract change is pre-approved for Round 4.

Any backward-incompatible or wire-semantic shared contract change requires a concrete Change Request and Chat-6 decision before implementation/integration.

## Current state machine

```text
ROUND_3_CLOSED
    -> ROUND_4_STAGE0_COMPLETE
    -> ROUND_4_WORKER_INTAKE_ACTIVE
    -> ROUND_4_STAGE1_REVIEW_PENDING
    -> INTEGRATION_PASS_4_CANDIDATE_NOT_AUTHORIZED
```
