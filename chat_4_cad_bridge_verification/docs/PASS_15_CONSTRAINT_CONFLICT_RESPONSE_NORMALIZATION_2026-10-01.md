# Chat 4 — Pass 15 Constraint-Conflict Response Normalization

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-15`  
**Worker base:** shared `main@99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

## Purpose

The canonical CAD verification model already distinguishes `CONSTRAINT_CONFLICT`, but the SOLIDWORKS adapter boundary previously accepted `read_back.constraint_conflicts` with almost no shape validation. In particular, a JSON string could be converted into a Python `frozenset` of characters, duplicate IDs were silently collapsed, and unknown conflict IDs were left to fail later through a less specific boundary error.

Pass 15 hardens the SOLIDWORKS process-response boundary without changing shared canonical contracts.

## Implemented

`src/mrea_cad_bridge/solidworks_agent.py` now validates `read_back.constraint_conflicts` before constructing `CadReadBack`:

- the field must be a JSON-array-compatible list/tuple;
- every entry must be a non-empty string dimension ID;
- duplicate conflict dimension IDs fail closed instead of being silently deduplicated;
- every conflict ID must reference a dimension already bound by the worker response;
- malformed `read_back` values are normalized to `CadAdapterError` instead of leaking incidental attribute/type errors.

A valid conflict array remains vendor-neutral after parsing as `CadReadBack.constraint_conflicts` and is consumed unchanged by `execute_cad_transfer_v1` / `VerificationEngine`.

## Canonical result

A valid SOLIDWORKS response containing a bound conflict dimension ID now deterministically reaches the existing canonical report as:

```text
status = CONSTRAINT_CONFLICT
difference = null
overall_status = FAILED
```

No verified physical measurement is rewritten or corrected.

## Tests

`tests/test_solidworks_constraint_conflict_response.py` covers:

- valid conflict preservation;
- end-to-end SOLIDWORKS adapter response → canonical `CONSTRAINT_CONFLICT` report;
- rejection of string-shaped conflict payloads;
- duplicate IDs;
- unknown/unbound IDs;
- non-string IDs;
- non-object `read_back` payloads.

## Scope boundary

This pass normalizes and validates solver-conflict evidence received from the SOLIDWORKS worker. It does **not** claim that the current C# worker newly detects every possible SOLIDWORKS solver conflict.

Current production worker code still owns real-host detection. Existing hard failures such as unsupported relation creation or general CAD API failures remain hard failures unless the worker emits a valid bound `constraint_conflicts` dimension ID.

SOLIDWORKS API 2026 distinguishes `swSetValue_DrivenDimension` from generic set-value failure and exposes `swOverDefining` as a sketch-relation filter. A future worker-side detection change may use those signals, but Pass 15 deliberately does not infer a solver conflict from an arbitrary worker failure.

## Host qualification

`solidworks_agent.py` is part of the standing SOLIDWORKS host-boundary fingerprint. This pass therefore changes that fingerprinted boundary even though it is software-only. Positive real-host qualification, when required, remains owned exclusively by `.github/workflows/solidworks_host_qualification.yml` and cannot be inferred from Linux CI.
