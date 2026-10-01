# Final-Orchestrator Addendum — SOLIDWORKS Standing Qualification

**Date:** 2026-10-01  
**Authority:** Orchestrator 2 / final orchestrator 2 of 2  
**Directive:** `OD-2026-10-01-006`

## Decision

The repeated Round-3-to-Round-12 external labels for production C# interop build, real SOLIDWORKS 2026 host execution and native SLDPRT generation/read-back are retired as per-round closure fields.

They describe one environment qualification and are now governed by `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md` and `.github/workflows/solidworks_host_qualification.yml`.

## Round 12 effect

Round 12 remains historically certified exactly as recorded. Operationally, however, its software state is green and closed:

```text
ROUND_12_CLOSED = TRUE
ROUND_12_SOFTWARE_STATUS = GREEN
OPEN_SOFTWARE_BLOCKERS = NONE
```

An unexecuted standing SOLIDWORKS host qualification no longer changes an ordinary round verdict to `ACCEPTED_WITH_EXTERNAL_GATE`.

## Future final-certification rule

Final orchestrators must not copy these three legacy lines into ordinary round certifications:

- `REAL_SOLIDWORKS_2026_HOST = ...`
- `PRODUCTION_CSHARP_INTEROP_BUILD = ...`
- `NATIVE_SLDPRT_GENERATION_READBACK = ...`

Instead, consult the standing qualification only when:

1. its state changed;
2. a fingerprinted SOLIDWORKS host-boundary file changed since the last successful qualification;
3. the controlled host changed materially; or
4. the round explicitly targets real SOLIDWORKS runtime behavior.

If none applies, the standing qualification is out of the round report.

## Truth constraint

This addendum changes orchestration/reporting semantics only. It does not claim a real-host run occurred. The first positive qualification must still come from the dedicated controlled-host workflow and its generated `solidworks_host_qualification.json` evidence.
