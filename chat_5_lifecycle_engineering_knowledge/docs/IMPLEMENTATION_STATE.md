# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-29**
- Branch: `chat-5/pass-2`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Orchestrator directive: **OD-2026-09-29-002**
- State: **Pass 2 CAD verification → lifecycle gate implemented and locally verified**

## Accepted baseline from Pass 1

Still active:

- Revision / Manufacturing / Installation / Test / Failure domain;
- lifecycle services;
- timeline and equipment registry;
- lifecycle state projection;
- revision comparison;
- deterministic knowledge queries;
- `CanonicalLifecycleEventAdapter` for `mrea.lifecycle-event.v1`;
- evidence-preserving canonical lifecycle export.

## Pass 2 additions

### Models

- `RevisionOrigin` (`MANUAL`, `CAD_TRANSFER`);
- `CADVerificationStatus` (`VERIFIED`, `FAILED`);
- `CADArtifactReference` internal snapshot;
- `CADRevisionLink`;
- `Revision.origin`;
- `Revision.cad_link`.

### Application path

- `CADRevisionPreparationService`;
- canonical CADPackage schema/version checks;
- canonical CADVerificationReport schema/version checks;
- package/report ID linkage validation;
- CAD artifact traceability retention;
- explicit CAD manufacturing eligibility gate.

### Manufacturing rule

For `RevisionOrigin.CAD_TRANSFER`:

```text
verification_status == VERIFIED → eligible
verification_status == FAILED   → blocked
missing CAD link                 → invalid revision
```

No silent override exists.

The explicit `MANUAL` origin preserves the pre-existing Phase-1 internal/manual flow and is not treated as a CAD verification result.

## Canonical inputs

Consumed without modification:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/cad_package_v1.json`;
- `tests/fixtures/contracts/cad_verification_v1.json`;
- `tests/fixtures/contracts/lifecycle_event_v1.json`.

Shared contracts remain owned by Chat 6.

## Tests

Full Chat 5 suite:

```text
PYTHONPATH=src pytest -q
13 passed
```

New coverage:

- VERIFIED CAD → Revision → manufacturing;
- FAILED CAD retained but manufacturing rejected;
- `cad_package_id` mismatch rejected;
- `sketch_package_id` mismatch rejected;
- CAD IDs/artifacts retained;
- metadata defensive copy;
- missing/non-canonical verification rejected;
- existing canonical LifecycleEvent export unchanged.

## Files added in Pass 2

- `tests/test_cad_lifecycle_linkage.py`;
- `docs/PASS_2_CAD_LIFECYCLE_LINKAGE.md`;
- `ORCHESTRATOR_HANDOFF.md` (written after tested implementation SHA is known).

## Files modified in Pass 2

- `src/mrea_lifecycle/models.py`;
- `src/mrea_lifecycle/services.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`.

## Not implemented

- production persistence;
- repository abstraction;
- physical instance/removal/replacement semantics;
- REST/API;
- concurrency/versioning;
- migrations;
- semantic search / AI.

## Next step

Do not continue past this integration gate until Chat 6 reviews Pass 2 and issues the next directive.
