# CHANGE_REQUEST_001 — CAD Contract Baseline

**Requester:** Chat 4 — CAD Bridge & Verification  
**Дата:** 2026-09-29  
**Status:** RESOLVED / CLOSED  
**Resolved by:** Chat 6 / Orchestrator canonical baseline `mrea.contracts.v1`

## Original request

Chat 4 запросил canonical:

- `SketchPackage v1`;
- `CADPackage v1`;
- `CADVerificationReport v1`;
- stable ID policy;
- units/coordinate policy;
- CAD transfer tolerance;
- mandatory geometry subset;
- unsupported geometry policy;
- canonical fixtures.

## Resolution

Orchestrator опубликовал:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/sketch_package_v1.json`;
- `tests/fixtures/contracts/cad_package_v1.json`;
- `tests/fixtures/contracts/cad_verification_v1.json`.

Canonical решения:

- IDs — opaque non-empty strings;
- `SketchPackage v1` coordinate system — `MAT_XY_MM`;
- mandatory geometry — `POINT`, `LINE`, `CIRCLE`, `ARC`;
- unsupported geometry — explicit `unresolved`;
- verification primary ID — `dimension_id`;
- `measurement_id` — nullable traceability link;
- transfer tolerance — `1e-6 mm` / `1e-6 deg`;
- item statuses — `VERIFIED`, `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT`;
- report overall status — `VERIFIED` / `FAILED`.

## Chat 4 migration

Выполнено:

- internal verification key изменён `measurement_id → dimension_id`;
- `measurement_id` сохранён как отдельная nullable link;
- canonical SketchPackage mapper добавлен;
- canonical CADPackage builder добавлен;
- canonical CADVerificationReport mapper добавлен;
- golden contract tests добавлены;
- local tolerance guess заменён canonical policy.

Backward-incompatible shared contract change не выполнялся.

## Result

Change Request закрыт. Новый Change Request нужен только при необходимости изменить `mrea.contracts.v1`.
