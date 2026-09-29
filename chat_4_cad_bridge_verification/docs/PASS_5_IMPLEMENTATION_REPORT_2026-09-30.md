# Chat 4 — Pass 5 Implementation Report

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-5`  
**Base:** frozen Pass-3 head `08beb9c45cdc1bbbcdebe220059a64288a880095`  
**Review PR:** `#28` (`chat-4/pass-5` -> `chat-4/pass-3`, draft)

## Why Pass 5

A historical `chat-4/pass-4` branch already existed, but it diverged before the final Side Chat 4B reconciliation into Pass 3. It was therefore not merged blindly.

Pass 5 starts from the final frozen Pass-3 result and reconciles the useful vendor-neutral runtime-validation concept from the old Pass-4 work onto that correct baseline.

No canonical/shared contract or Chat-6-owned CI file is changed.

## Delivered

### 1. Unified direct runtime-validation API

Added:

`src/mrea_cad_bridge/runtime_validation.py`

with:

- `CadRuntimeValidationExecution`;
- `execute_cad_runtime_validation_v1(...)`;
- pre-transfer fail-closed host readiness;
- adapter/readiness identity check;
- explicit SOLIDWORKS version requirement for direct real-host execution;
- generic/test-double numerical verification with runtime status remaining `UNVERIFIED`.

### 2. Side 4B facts -> Primary runtime-validation path

Added:

- `SolidWorksRuntimeValidationExecution`;
- `evaluate_solidworks_runtime_inputs_v1(...)`.

For successful Side 4B runtime-input bundles the function:

1. validates raw evidence shape before Pass-3 parsing;
2. reuses `parse_solidworks_runtime_inputs_v1`;
3. cross-checks host/worker version evidence;
4. reuses the existing Pass-3 `build_solidworks_runtime_evidence_from_inputs_v1` path;
5. replays the recorded vendor-neutral result through `execute_cad_runtime_validation_v1`;
6. requires both Primary paths to produce exactly identical runtime evidence.

Nonzero agent exits remain evidence-only and do not fabricate a canonical transfer execution.

### 3. SOLIDWORKS 2026 cross-evidence hardening

Primary now checks:

- worker `solidworks_version` parses as a RevisionNumber major;
- required major is exactly `34` for the SOLIDWORKS 2026 adapter baseline;
- host-readiness `SOLIDWORKS_VERSION_2026` exists;
- successful agent execution requires that readiness check to be `PASS`;
- optional readiness `revision_number` must equal worker `solidworks_version`;
- optional readiness `revision_major` must equal the worker major;
- optional readiness `expected_revision_major` must equal the Primary baseline `34`.

This prevents mutually inconsistent host and worker evidence from producing final runtime `VERIFIED`.

### 4. Raw conflict evidence hardening

`constraint_conflicts` is checked before the Pass-3 parser.

It must be an array of non-empty strings. Numeric/object values are rejected explicitly as:

`SOLIDWORKS_RUNTIME_CONFLICTS_INVALID`

instead of being silently coerced with `str(...)` before validation.

## Tests added

`tests/test_runtime_validation.py`

10 direct runtime-validation tests covering:

- generic numerical verification / runtime UNVERIFIED;
- missing readiness;
- failed readiness;
- unverified readiness;
- adapter identity mismatch;
- missing version;
- successful recorded real-host path;
- numerical mismatch;
- missing native artifact;
- runtime error diagnostic.

`tests/test_runtime_validation_side_inputs.py`

7 Side-input integration/hardening tests covering:

- successful Side bundle replay through the direct runtime path;
- worker revision-major mismatch;
- host/worker revision-number mismatch;
- host/worker revision-major mismatch;
- malformed constraint-conflict type;
- nonzero worker exit without fake transfer execution;
- preservation of existing canonical-report tamper detection.

## CI evidence

First implementation run identified one intended hardening-order defect:

- run `36637995116`;
- Chat 4: 77/78 passing;
- malformed conflict test reached the old parser before the new raw-shape check.

This was corrected by validating the raw conflict field before Pass-3 parsing.

Corrected implementation SHA:

`cd94b1ee47e33359ca913a8110a98100456b0e94`

Corrected CI run:

`36638190512` — `SUCCESS`

Verified on that SHA:

- Chat 4 / Generic CAD gate: **SUCCESS**;
- Chat 4 suite: **78 tests, OK**;
- Contracts / canonical fixtures: **SUCCESS**;
- Integration / Chat 3 -> Chat 4: **SUCCESS**;
- Integration / Chat 4 -> Chat 5: **SUCCESS**.

## Ownership

Preserved unchanged:

- canonical shared contracts;
- canonical verification semantics;
- Primary Pass-3 `runtime_evidence.py`;
- Side-local `mrea.solidworks-runtime-inputs.v1` remains slice-local;
- Chat-6-owned workflow/integration files.

## Runtime truth

No actual Windows 11 + installed SOLIDWORKS 2026 execution occurred in this pass.

Therefore:

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

Synthetic/pure evidence tests do not promote those statuses.

## Next integration note

This branch is layered on the final frozen Pass-3 branch rather than on the stale diverged historical Pass-4 branch. The historical Pass-4 branch should not be blindly merged into this line.
