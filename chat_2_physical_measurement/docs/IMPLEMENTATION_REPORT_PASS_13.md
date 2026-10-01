# Chat 2 — Pass 13 Implementation Report

## Baseline

Pass 13 starts from certified shared `main`:

`4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`

Directive: `OD-2026-10-01-005`.

## Goal

Close the explicit offline-first persistence gap in Chat 2 without changing shared contracts or downstream normalization.

Before this pass the only repository was in-memory, so pending measurements, evidence references and confirmation state disappeared when the process ended.

## Implementation

Added `MeasurementSessionRepository` Protocol and `SqliteMeasurementSessionRepository`.

The SQLite repository:

- stores sessions transactionally in a local SQLite database;
- persists one versioned private Chat-2 payload per session;
- preserves Decimal values as strings rather than lossy floats;
- preserves timezone-aware created/confirmed timestamps;
- preserves measurement type/unit/source/provenance, 1..3 ordered anchors, evidence frame, instrument and unit-neutral uncertainty;
- preserves unverified candidates across repository/process re-open;
- preserves `USER_CONFIRMED` state after confirmation;
- rejects unknown local schema versions;
- fails closed on corrupted stored payloads;
- keeps missing-session behavior compatible with the existing repository.

`MeasurementSessionService` now depends on the repository Protocol rather than the concrete in-memory implementation. The in-memory repository remains available.

## Storage ownership

The persisted JSON is explicitly a private Chat-2 local storage format:

`mrea.chat2.measurement-session.local.v1`

It is not a canonical/shared contract and does not modify `core/contracts/`.

SQLite is reused from the Python standard library; no ORM or third-party database dependency is added.

## Tests

Added `tests/test_pass13_local_persistence.py` covering:

1. pending device candidate survives repository re-open;
2. evidence/instrument/provenance/uncertainty survive re-open;
3. explicit confirmation survives a second re-open;
4. three-anchor angular measurement and degree uncertainty round-trip losslessly;
5. corrupted JSON payload fails closed;
6. unsupported local persistence schema fails closed;
7. missing session preserves existing `KeyError` semantics.

## Ownership / boundaries

Only `chat_2_physical_measurement/` is changed.

No shared contract, fixture, Chat-1/3/4/5 source, shared CI or downstream coordinate normalization is modified.

## Remaining persistence debt

- no session enumeration/query API yet;
- no explicit migration runner beyond fail-closed schema versioning;
- no multi-process stress/load benchmark yet;
- no encryption-at-rest policy has been introduced by Chat 2;
- application composition still must choose the durable repository in the runtime layer.
