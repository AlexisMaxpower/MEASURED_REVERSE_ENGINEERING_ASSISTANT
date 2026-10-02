# Chat 2 — Pass 17 Build / Reuse Check

## Problem

`MeasurementSession` is durable, but the hands-free controller state is process-local. After a restart, an unverified physical-measurement candidate can still exist in SQLite while a newly constructed controller starts in `IDLE` and therefore cannot safely confirm, reject or correct that candidate.

## Existing building blocks

Reuse:

- durable `MeasurementSessionService` / `MeasurementSessionRepository`;
- persisted `PhysicalMeasurement` truth, anchors, evidence, provenance and confirmation state;
- existing `HandsFreeMeasurementController` transitions;
- existing SQLite private persistence format.

Do not add:

- a second workflow-state database;
- a new shared/canonical contract;
- a generic state-machine or workflow dependency;
- heuristic "latest candidate" selection.

## Decision

Add a Chat-2-local recovery layer that reconstructs only the actionable `CANDIDATE_PENDING` interaction state from durable session truth.

Recovery policy:

```text
0 exact pending matches -> IDLE
1 exact pending match   -> CANDIDATE_PENDING
>1 exact pending match  -> fail closed
explicit measurement_id -> recover only that exact unverified/context-matching candidate
```

The context match includes measurement type, view, ordered anchors, evidence frame, instrument and uncertainty. This prevents a controller from attaching itself to a physically different measurement merely because both values are unverified.

## Why derive instead of persist controller state

`AWAITING_VALUE`, `VERIFIED` and `REJECTED` are interaction states, not additional measurement truth. The durable facts already live in `MeasurementSession`.

Persisting a second state payload would introduce synchronization/migration debt and could disagree with measurement truth. Derivation keeps one source of truth and allows existing Pass-13/15 SQLite data to participate without schema migration.

## Fail-closed behavior

- multiple matching pending candidates are never ordered or guessed;
- verified measurements cannot be resumed as pending;
- explicit IDs must exist, remain unverified and match the supplied context;
- context mismatch does not mutate the session;
- transient `AWAITING_VALUE` is intentionally lost on restart and returns to `IDLE` because no candidate fact exists yet.

## Lock-in

Low. Recovery consumes the existing service boundary and returns the existing controller type. No persistence provider or speech provider is coupled into the recovery contract.
