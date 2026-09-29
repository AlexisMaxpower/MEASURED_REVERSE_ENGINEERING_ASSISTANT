# Side Chat 4B — Pass 3 Task

**Parent slice:** Chat 4 — CAD Bridge & Verification  
**Directive:** `OD-2026-09-29-003`  
**Primary baseline main SHA:** `c3452d7fa68c9c5c3716db5fef71172e9c3b9532`  
**Recommended branch:** `chat-4b/pass-3`

## Mission

Implement the SOLIDWORKS/Windows half of Pass 3 without changing canonical contracts or Primary Chat 4 verification semantics.

Primary Chat 4 owns the slice-local readiness/evidence semantics in:

- `src/mrea_cad_bridge/runtime_evidence.py`;
- `docs/RUNTIME_EVIDENCE_V1.md`.

Your job is to supply truthful host/runtime facts to that boundary.

## Required work

### Fail-closed host preflight

Implement deterministic checks for:

- Windows 11 x64;
- x64 process;
- .NET Framework/build prerequisites where detectable;
- CAD Agent executable/build readiness;
- `SldWorks.Application` COM registration;
- installed/running SOLIDWORKS version and 2026 compatibility;
- SOLIDWORKS interop/API assembly availability;
- writable output/artifact directory;
- usable part template path/default template.

Unknown required facts are `UNVERIFIED`, never `PASS`.

### Machine-readable output

Produce `mrea.cad-host-readiness.v1` data. Each check includes `code`, `status`, `message`, `required`, and optional `details`.

Primary Chat 4 recomputes aggregate readiness; do not rely on a hand-written READY flag.

### Stable diagnostics

Return stable `code`, `stage`, `message`, `severity`, `details` for failures. Suggested stages:

- `HOST_PREFLIGHT`;
- `AGENT_STARTUP`;
- `SOLIDWORKS_COM`;
- `CAD_TRANSFER`;
- `READ_BACK`;
- `ARTIFACT`.

### Process exit classes

Suggested mapping:

- `0` — completed successfully;
- `10` — host preflight not ready;
- `20` — invalid request/protocol/input;
- `30` — SOLIDWORKS/COM startup failure;
- `40` — CAD transfer/rebuild/read-back failure;
- `50` — artifact save/evidence failure;
- `70` — unexpected internal failure.

If the existing worker already has a better stable mapping, document it instead of silently changing semantics.

### One-command golden procedure

Provide a deterministic Windows command that runs:

`preflight -> build/locate agent -> golden transfer -> SOLIDWORKS -> rebuild/read-back -> save .SLDPRT -> emit evidence inputs`.

Do not print runtime `VERIFIED` just because the process launched. Primary Chat 4 runtime evidence + canonical VerificationEngine own that decision.

### Runtime facts to return

- actual SOLIDWORKS version;
- input `sketch_package_id`;
- bindings/vendor refs;
- normalized read-back dimensions;
- artifact identity/URI/SHA-256;
- failure diagnostics.

## Ownership boundaries

Primary SOLIDWORKS ownership areas:

- `solidworks_agent/`;
- SOLIDWORKS-specific scripts;
- `docs/SOLIDWORKS_*.md`.

Avoid editing:

- `src/mrea_cad_bridge/runtime_evidence.py`;
- `tests/test_runtime_evidence.py`;
- `core/contracts/`;
- `tests/fixtures/contracts/`;
- Chat-6-owned CI/integration tests.

If the evidence boundary is insufficient, report the gap to Primary Chat 4.

## Verification status

Without an actual Windows 11 + installed SOLIDWORKS 2026 execution:

`REAL_HOST = UNVERIFIED`

No simulated/inferred PASS.

## Handoff

Finish with `chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md` containing Pass/directive, branch, final SHA, changed files, checks implemented, exit codes, exact tests/builds, C# compilation status, real-host status, limitations, and requested integration action.
