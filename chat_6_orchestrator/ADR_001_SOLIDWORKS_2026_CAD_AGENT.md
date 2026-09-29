# ADR-001 — SOLIDWORKS 2026 CAD Agent Baseline

**Status:** ACCEPTED  
**Date:** 2026-09-29  
**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Resolves:** `chat_4_cad_bridge_verification/docs/CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md`

## Context

Chat 4 completed a vendor-neutral `CadAdapter` / normalized read-back / verification boundary. The next implementation stage requires a concrete environment for a real SOLIDWORKS adapter.

The project owner currently uses SOLIDWORKS 2026 on Windows 11. MREA must preserve a platform-neutral canonical core while isolating SOLIDWORKS/COM concerns.

## Decision

### Target environment

- OS: **Windows 11 x64**.
- CAD: **SOLIDWORKS 2026 x64** for the first verified adapter baseline.
- Language: **C#**.
- Runtime baseline: **.NET Framework 4.8** for the first COM adapter implementation.
- Process architecture: **x64**.

This baseline is intentionally narrow for v1. Wider SOLIDWORKS-version compatibility can be added only after the 2026 adapter is verified end-to-end.

### Adapter topology

The first real SOLIDWORKS integration SHALL run as an **out-of-process user-session CAD Agent / worker process** behind the existing vendor-neutral `CadAdapter` semantics.

It SHALL NOT initially be:

- a Windows service;
- a mandatory in-process SOLIDWORKS add-in;
- part of the canonical Python domain runtime.

Reasons:

- isolate COM/SOLIDWORKS lifecycle failure from canonical domain logic;
- keep generic tests runnable without SOLIDWORKS;
- make attach/launch/debug behavior explicit;
- preserve the possibility of a later in-process add-in without changing shared contracts.

### COM policy

- SOLIDWORKS COM interaction runs on a dedicated **STA** thread/process execution context.
- COM objects are not passed across arbitrary worker threads.
- adapter shutdown must release vendor objects deterministically where practical and treat failed/partial transfer as adapter failure, never verification success.

### Interop references

- Prefer official SOLIDWORKS 2026 API/interop assemblies available from the locally installed SOLIDWORKS/API SDK environment.
- Do not vendor proprietary SOLIDWORKS binaries into the repository unless licensing and redistribution are explicitly confirmed.
- Build documentation must describe how a developer resolves local SOLIDWORKS interop references.

### Canonical boundary

SOLIDWORKS-specific code must remain behind Chat 4's existing adapter boundary:

```text
SketchPackage v1
→ MappedSketchPackage
→ SolidWorksCadAdapter
→ SOLIDWORKS COM/API
→ normalized CadReadBack
→ VerificationEngine
→ CADVerificationReport v1
```

The canonical layer remains vendor-neutral.

### Units and identity

- canonical length: `mm`;
- canonical angle: `deg`;
- CAD transfer tolerance remains `1e-6 mm` / `1e-6 deg` for numerical-transfer verification;
- `dimension_id` remains the verification identity;
- `measurement_id` remains traceability back to physical evidence;
- vendor references must never replace canonical identities.

### Integration-test host

Real SOLIDWORKS tests require a host with:

- Windows 11 x64;
- SOLIDWORKS 2026 installed and launchable;
- required API/interop components;
- user-session desktop access.

Generic contract/test-double tests remain independent of this host.

If no real SOLIDWORKS host is available, the SOLIDWORKS integration gate is **UNVERIFIED/SKIPPED**, never PASS.

A release must not claim the real SOLIDWORKS adapter verified until at least one supported host has executed the integration smoke/golden test successfully.

### Native CAD artifacts

Generated native files are treated as artifacts of the existing CAD boundary:

1. CAD Agent writes to a controlled local working directory;
2. resulting files are registered through existing artifact/CADPackage semantics;
3. Chat 4 must not invent a second storage system;
4. persistent storage policy remains outside the vendor adapter.

## First SOLIDWORKS acceptance slice

Do not attempt all CAD behavior at once.

First real-host gate:

1. start/attach to SOLIDWORKS 2026;
2. create a new part document;
3. create one FRONT sketch;
4. map the mandatory v1 primitives needed by the golden part;
5. create the verified dimensions supported by that sketch;
6. preserve `dimension_id ↔ measurement_id ↔ vendor_dimension_ref` mapping;
7. read dimensions back from SOLIDWORKS;
8. normalize to canonical units;
9. produce CADVerificationReport;
10. save/register the native artifact.

Unsupported relations/features must fail explicitly or remain unresolved; no silent approximation.

## Consequences

Positive:

- vendor integration is isolated;
- existing TEST_DOUBLE remains useful;
- Python/core code stays platform-neutral;
- COM crashes/lifecycle issues do not define domain architecture.

Trade-offs:

- requires a Windows + SOLIDWORKS host for final verification;
- adds a process boundary;
- initial adapter targets one SOLIDWORKS major version rather than pretending broad compatibility.

## Reference material

- SOLIDWORKS API Getting Started: https://help.solidworks.com/2026/english/api/sldworksapiprogguide/GettingStarted/SolidWorks_API_Getting_Started_Overview.htm
- SOLIDWORKS API SDK overview/templates: https://help.solidworks.com/2026/english/api/sldworksapiprogguide/GettingStarted/SOLIDWORKS_API_SDK.htm
- SOLIDWORKS system requirements: https://www.solidworks.com/support/system-requirements
