# BUILD / REUSE CHECK — SOLIDWORKS Host Readiness / Pass 3

**Owner:** Side Chat 4B  
**Directive:** `OD-2026-09-29-003`  
**Fix:** `ORCHESTRATOR_FIX_REQUIRED_PASS3.md`

## Existing components reused

The correction reuses rather than replaces:

- canonical `SketchPackage v1` fixture and mapping;
- `SolidWorksAgentConfig` and request builder;
- existing out-of-process `mrea.solidworks-agent.v1` boundary;
- existing C# SOLIDWORKS worker/project;
- existing LINE/CIRCLE + dimension transfer implementation;
- existing canonical `execute_cad_transfer_v1` verification pipeline;
- existing native `.SLDPRT` artifact creation and SHA-256 metadata;
- Primary Chat 4 `mrea.cad-host-readiness.v1` specification.

## New code justified

### Windows host-readiness probe

No existing component queried Windows/.NET/COM/SOLIDWORKS/template/output readiness and emitted the required machine-readable readiness payload. A SOLIDWORKS-specific PowerShell probe is therefore required.

### Evidence-input producer

The existing golden runner only executed the canonical transfer and previously printed a real-host VERIFIED marker from numerical success alone. It did not preserve raw agent exit/diagnostics/version/read-back/artifact facts for Primary Chat 4. A side-local producer is added instead of modifying Primary-owned `runtime_evidence.py`.

### Stable worker diagnostics

The existing worker returned a single generic nonzero exit code and text exception. Pass 3 explicitly requires machine-readable failure reasons and stable exit classes, so the existing process envelope is extended without changing the protocol identifier or canonical contracts.

## Not duplicated

This correction does **not** implement another:

- canonical verification engine;
- CAD package/report contract;
- shared runtime-evidence authority;
- second CAD storage system;
- second SOLIDWORKS geometry engine.

The producer reuses canonical verification by wrapping the already returned `CadAdapterResult` in a recorded one-shot adapter; SOLIDWORKS is not executed twice.

## Ownership preserved

Not edited:

```text
src/mrea_cad_bridge/runtime_evidence.py
tests/test_runtime_evidence.py
core/contracts/
tests/fixtures/contracts/
.github/workflows/
tests/integration/
```

Primary Chat 4 remains responsible for integrating the produced host/runtime facts into final Pass-3 runtime evidence and handoff.
