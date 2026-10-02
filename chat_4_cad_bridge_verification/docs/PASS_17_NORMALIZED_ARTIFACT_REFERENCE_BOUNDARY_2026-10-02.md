# Chat 4 — Pass 17 Normalized Artifact Reference Boundary

**Date:** 2026-10-02  
**Branch:** `chat-4/pass-17`  
**Base:** shared `main@933d925c69944d40859ae1f9ff80d7a3ecb7f760`

## Purpose

Round 16 closed the SOLIDWORKS success-response completeness gap, but the vendor-neutral `CadAdapterResult` boundary still accepted arbitrary artifact mappings. That allowed an adapter to construct a result containing an artifact that could not be represented by canonical `ArtifactReference` without the failure being detected until later schema validation.

Pass 17 makes normalized CAD adapter artifact evidence fail closed before `CADPackage` construction while leaving the shared canonical schema unchanged.

## Implemented

`CadAdapterResult.__post_init__` now validates every artifact against the structural surface of canonical `ArtifactReference`:

- each artifact must be a mapping/object;
- `artifact_id`, `kind`, and `uri` must be non-empty strings;
- only canonical artifact fields are accepted: `artifact_id`, `kind`, `uri`, `media_type`, `sha256`, `metadata`;
- `media_type` and `sha256` remain optional and may be string or null, matching the shared schema;
- `metadata`, when present, must be an object;
- `artifact_id` values must be unique within one adapter result.

The validation deliberately does not add semantics that the shared schema does not define. In particular, it does not require a SHA-256 value, prescribe a digest format, dereference URIs, or infer native-file existence.

## Failure semantics

Invalid normalized artifacts now fail at adapter-result construction rather than being copied into a potentially invalid canonical `CADPackage`.

The SOLIDWORKS response parser already normalizes `CadAdapterResult` construction failures to `CadAdapterError`; Pass 17 adds a regression test proving duplicate artifact identity evidence remains a vendor-boundary error instead of leaking a raw `ValueError`.

## Tests

`tests/test_adapter_artifact_boundary.py` covers:

- empty artifact sets;
- valid canonical artifact-reference shape;
- nullable optional `media_type` / `sha256`;
- non-object artifacts;
- missing, empty, and wrongly typed required identity fields;
- unknown/non-canonical fields;
- invalid optional scalar types;
- invalid metadata shape;
- duplicate `artifact_id` values;
- SOLIDWORKS parser normalization of artifact-boundary failures.

## Scope boundary

No canonical contract, shared fixture, shared CI workflow, SOLIDWORKS mutation logic, host script, capability fingerprint, measurement semantics, geometry semantics, or lifecycle code is changed.

This pass is software-only normalized-boundary hardening. It makes no new real-host claim and does not alter the standing `SOLIDWORKS_HOST_QUALIFICATION` authority.
