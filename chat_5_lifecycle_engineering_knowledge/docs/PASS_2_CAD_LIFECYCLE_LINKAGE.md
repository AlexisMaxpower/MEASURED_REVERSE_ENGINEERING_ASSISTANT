# Chat 5 — Pass 2: CAD Verification → Lifecycle Linkage

## Status

- Date: **2026-09-29**
- Branch: `chat-5/pass-2`
- Orchestrator directive: **OD-2026-09-29-002**
- Status: **implemented / locally verified**
- Shared contracts modified: **NO**

## Goal

Close the Chat 4 → Chat 5 boundary:

```text
canonical CADPackage
+ canonical CADVerificationReport
→ lifecycle Revision
→ manufacturing eligibility
→ existing lifecycle events
```

## Internal model additions

### `RevisionOrigin`

Explicitly separates:

- `MANUAL` — legacy/manual lifecycle revision path;
- `CAD_TRANSFER` — revision created from canonical CAD output.

This prevents CAD verification state from being represented as an implicit or silent boolean bypass.

### `CADRevisionLink`

A CAD-origin revision retains:

- `cad_package_id`;
- `sketch_package_id`;
- `cad_verification_report_id`;
- CAD adapter identifier;
- canonical CAD artifact snapshots;
- `CADVerificationReport.overall_status` as internal `CADVerificationStatus`.

### `CADArtifactReference`

Internal snapshot of each canonical `ArtifactReference` available in `CADPackage.artifacts`:

- `artifact_id`;
- `kind`;
- `uri`;
- `media_type`;
- `sha256`;
- `metadata`.

Artifact metadata is deep-copied at the boundary so later mutation of the input payload cannot rewrite retained lifecycle traceability.

## Application path

`CADRevisionPreparationService.prepare()` consumes canonical CAD payloads and:

1. checks canonical schema versions;
2. requires non-empty package/report IDs;
3. requires `CADVerificationReport.cad_package_id == CADPackage.cad_package_id`;
4. requires `CADVerificationReport.sketch_package_id == CADPackage.sketch_package_id`;
5. accepts only canonical `overall_status` values `VERIFIED` / `FAILED`;
6. snapshots all CAD artifact references;
7. creates a `Revision(origin=CAD_TRANSFER, cad_link=...)`;
8. emits the existing internal `REVISION_CREATED` event through `RevisionService`.

A FAILED report is retained as a traceable revision fact rather than discarded.

## Manufacturing eligibility

`ManufacturingService` now applies an explicit CAD-origin gate:

```text
RevisionOrigin.CAD_TRANSFER
        ↓
CADRevisionLink present?
        ↓
verification_status == VERIFIED?
        ↓
YES → manufacturing allowed
NO  → LifecycleInvariantError
```

A `FAILED` CAD transfer therefore cannot silently generate a `MANUFACTURED` event.

The existing manual Phase-1 path remains operational and explicitly identified as `RevisionOrigin.MANUAL`; it is not represented as a CAD verification override.

No override mechanism was introduced in Pass 2.

## Canonical boundary

No shared schema changes were made.

The existing `CanonicalLifecycleEventAdapter` remains unchanged. A VERIFIED CAD-origin revision that proceeds to manufacturing still exports the existing canonical events:

```text
REVISION_CREATED
MANUFACTURED
```

with the same `mrea.lifecycle-event.v1` wire shape.

Richer CAD traceability remains internal to Chat 5, as required by OD-002.

## Tests

Added `tests/test_cad_lifecycle_linkage.py`.

Coverage includes:

1. VERIFIED report → manufacturing eligible;
2. VERIFIED report → manufacturing succeeds;
3. FAILED report → revision retained but manufacturing blocked;
4. mismatched `cad_package_id` rejected;
5. mismatched `sketch_package_id` rejected;
6. CAD IDs retained on Revision;
7. CAD artifact references retained;
8. artifact metadata copied defensively;
9. missing/non-object verification report rejected;
10. non-canonical `UNVERIFIED` status rejected;
11. existing canonical lifecycle event export remains unchanged.

## Verification

Command:

```text
PYTHONPATH=src pytest -q
```

Result:

```text
13 passed
```

This includes all existing Chat 5 tests from Pass 1 plus the new Pass 2 gate tests.

## Limitations / next gate

Not implemented in this pass:

- production persistence;
- repository abstraction;
- physical part instance/removal/replacement semantics;
- REST/API;
- AI/semantic search;
- a manufacturing override mechanism.

The next step must be selected by the next Chat 6 directive after acceptance of this integration gate.
