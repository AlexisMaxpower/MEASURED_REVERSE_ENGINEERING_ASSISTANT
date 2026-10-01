# SOLIDWORKS Host Qualification Policy

**Revision:** `SWQ-2026-10-01-001`  
**Effective directive:** `OD-2026-10-01-006`

The following historical statuses are no longer independent round-level fields:

- `PRODUCTION_CSHARP_INTEROP_BUILD`
- `REAL_SOLIDWORKS_2026_HOST`
- `NATIVE_SLDPRT_GENERATION_READBACK`

They are three subchecks of one standing qualification: `SOLIDWORKS_HOST_QUALIFICATION`.

## Authoritative verification

Positive qualification requires a successful run of `.github/workflows/solidworks_host_qualification.yml` on a self-hosted Windows x64 runner with the custom label `solidworks-2026` and a real SOLIDWORKS 2026 installation.

That run must, in one execution:

1. verify Windows x64, .NET Framework, MSBuild, COM registration, SOLIDWORKS 2026 revision and official `api\redist` interops;
2. freshly compile `Mrea.SolidWorksCadAgent.exe` against those installed interops;
3. execute the real SOLIDWORKS COM host;
4. transfer the canonical sketch fixture;
5. save a native `.SLDPRT`;
6. read dimensions back from the real model;
7. verify native artifact existence and SHA-256;
8. replay runtime inputs through Primary Chat-4 evidence evaluation;
9. finish with runtime status `VERIFIED`;
10. emit `solidworks_host_qualification.json` with all three subchecks `VERIFIED`.

## Persistence

The qualification manifest records a `host_boundary_fingerprint` over the C# agent, host scripts, runtime-evidence bridge and canonical fixture.

A successful qualification remains valid across later ordinary software rounds while that fingerprint is unchanged and the controlled host has not materially changed.

Re-run only after a fingerprinted host-boundary file changes, the SOLIDWORKS major version changes, the controlled host is materially replaced, or previous evidence becomes invalid.

Unrelated Capture, Measurement, Geometry, generic CAD, Lifecycle, documentation or orchestration changes do not invalidate a successful qualification.

## Reporting rule

Ordinary worker/orchestrator reports must not repeat the three legacy `UNVERIFIED` lines. They should mention `SOLIDWORKS_HOST_QUALIFICATION` only when its state changes, the fingerprint becomes stale, or real SOLIDWORKS behavior is explicitly in scope.

An unexecuted standing qualification is not a software-round blocker and does not downgrade an otherwise green software round.

Never infer positive qualification from Linux CI, mocks, static checks, test doubles or a Windows runner without SOLIDWORKS.

## One-time host setup

Register one GitHub self-hosted runner on the Windows 11 x64 machine with SOLIDWORKS 2026 and add the label `solidworks-2026`.

After that, launch **MREA SOLIDWORKS 2026 Host Qualification** from GitHub Actions whenever qualification is needed. The evidence stays in the workflow run/artifact; no manual chat-to-chat handoff is required.

Local fallback from repository root:

```powershell
.\chat_4_cad_bridge_verification\scripts\qualify_solidworks_host.ps1
```

## Migration state

No real-host result is fabricated by introducing this policy. Until the first successful controlled-host run:

```text
SOLIDWORKS_HOST_QUALIFICATION = NOT_YET_EXECUTED_ON_REGISTERED_HOST
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```
