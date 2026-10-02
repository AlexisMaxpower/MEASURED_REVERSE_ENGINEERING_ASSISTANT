# Pass 19 — SOLIDWORKS subprocess success-claim gate

**Owner:** Chat 4 — CAD Bridge & Verification  
**Date:** 2026-10-02  
**Baseline:** `main@701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`  
**Branch:** `chat-4/pass-19`

## Purpose

The production C# CAD Agent already records process-level facts on every successful run:

- `real_host_executed = true`;
- `solidworks_version = <RevisionNumber()>`;
- `exit_code = 0`.

Before Pass 19, `SubprocessSolidWorksAgentRunner` accepted an `OK` JSON response without validating those success claims. The later normalized parser checked protocol/adapter/result evidence, but a malformed or contradictory subprocess envelope could reach that boundary.

## Change

The subprocess boundary now fails closed for an `OK` response unless all of the following are true:

1. response JSON is an object;
2. the OS process return code is zero when `status=OK`;
3. `real_host_executed` is exactly boolean `true`;
4. `exit_code` is exactly integer `0` (boolean/string substitutes are rejected);
5. `solidworks_version` is a non-empty string whose revision major is `34`, the SOLIDWORKS 2026 adapter baseline.

Failure responses are not promoted or reinterpreted by this gate; they continue to the existing error parser and remain non-success.

## Scope boundary

This is a **process-response consistency gate**, not positive real-host qualification.

Unit tests use a mocked subprocess only to prove fail-closed protocol behavior. They do not prove that SOLIDWORKS executed. Positive real-host truth remains owned exclusively by `.github/workflows/solidworks_host_qualification.yml` under `SOLIDWORKS_HOST_QUALIFICATION_POLICY.md`.

No canonical schema, shared CI workflow, Geometry, Measurement, Capture or Lifecycle code is changed.

## Host qualification effect

`src/mrea_cad_bridge/solidworks_agent.py` is part of the standing host-boundary fingerprint. Therefore this pass changes that fingerprinted boundary. Any previously positive host qualification is reusable only if its manifest fingerprint matches the post-Pass-19 boundary and the controlled host remains materially unchanged.

## Regression coverage

`tests/test_solidworks_subprocess_success_claims.py` covers:

- valid success claims;
- missing/false/non-boolean real-host claim;
- missing/nonzero/non-integer response exit code;
- missing/malformed/wrong-major SOLIDWORKS version;
- nonzero OS process exit while claiming `OK`;
- error responses remaining errors rather than being treated as success;
- non-object JSON response rejection.
