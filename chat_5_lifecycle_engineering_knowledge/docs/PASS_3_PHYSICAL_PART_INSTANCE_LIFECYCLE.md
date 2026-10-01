# Pass 3 — Physical Part Instance Lifecycle

## Directive

Implemented for:

- `OD-2026-09-29-003`;
- branch `chat-5/pass-3`;
- accepted contract baseline `mrea.contracts.v1`.

## Problem closed by this pass

Before Pass 3 the lifecycle could answer:

- which revision existed;
- how it was manufactured;
- where a revision/manufacturing record was installed;
- what tests or failures were recorded.

It did not have a first-class identity for the **specific real item** that was printed/machined and then lived in equipment.

That prevented reliable answers to questions such as:

- which exact printed copy failed;
- whether that exact copy had been tested before service;
- whether the failed copy was physically removed;
- which exact replacement occupies the position now;
- whether two records accidentally claim the same equipment/position.

## Domain choice

Pass 3 adds an internal physical-instance layer without changing the shared lifecycle contract.

```text
Revision
  |
ManufacturingRecord
  |
PhysicalPartInstance
  |
PhysicalLifecycleEvent[]
```

`PhysicalPartInstance` is tied to exactly one `ManufacturingRecord` and therefore exactly one revision.

Manufacturing material/method and selected manufacturing metadata are snapshotted onto the physical identity so later engineering history remains interpretable even before production persistence exists.

## State machine

### Main path

```text
MANUFACTURED
→ INSTALLED
→ TESTED
→ ACTIVE
```

### Failure path

```text
INSTALLED / TESTED / ACTIVE
→ FAILED
→ REMOVED
→ SUPERSEDED
```

### Preventive replacement path

```text
INSTALLED / TESTED / ACTIVE
→ REMOVED
→ SUPERSEDED
```

`SUPERSEDED` is terminal for the old physical item.

The replacement item has its own independent lifecycle and must already be installed/tested/active at the old equipment/position before the old item can be marked superseded.

## Test gate

A physical test carries an explicit internal `PhysicalTestOutcome`:

- `PASSED`;
- `FAILED`.

`ACTIVE` is allowed only when the latest physical event is a `TESTED` event with outcome `PASSED`.

This avoids parsing free-text `TestRecord.result` to decide whether a part is safe to enter service.

## Installation occupancy

`PhysicalEquipmentRegistry` derives current occupancy from the latest physical event of every instance.

States considered physically occupying equipment:

- `INSTALLED`;
- `TESTED`;
- `ACTIVE`;
- `FAILED`.

A second physical instance cannot be installed into the same `equipment_id + position` until the previous instance is removed.

A failed instance is still treated as occupying its location until an explicit `REMOVED` transition is recorded.

## Evidence and traceability

The physical application path requires `instance_id` on:

- `Installation`;
- `TestRecord`;
- `FailureRecord`.

For tests and failures the service verifies that revision, manufacturing record and installation all correspond to the same physical instance.

Failure evidence remains on the existing `FailureRecord`; physical events reference the same `failure_id`, preserving both revision-level and instance-level traceability.

## Chronology

Physical events have their own monotonic sequence.

For one physical instance:
- timestamps must be timezone-aware;
- a new event cannot occur earlier than the previous physical event.

Equal timestamps are allowed and remain deterministic through event sequence.

## Shared contract boundary

No changes were made to:

- `core/contracts/`;
- canonical fixtures;
- Chat-6-owned integration tests.

Shared `LifecycleEvent v1` remains unchanged.

Canonical event types remain:

```text
REVISION_CREATED
MANUFACTURED
INSTALLED
TESTED
FAILED
```

Physical-only facts:

```text
ACTIVATED
REMOVED
SUPERSEDED
instance_id
replacement_instance_id
test_outcome
```

remain internal to Chat 5.

## CAD eligibility invariant

The physical layer never creates a manufacturing record.

A `PhysicalPartInstance` can only be registered from an already existing `ManufacturingRecord`.

Therefore the existing rule remains intact:

```text
CAD_TRANSFER + VERIFIED -> ManufacturingRecord may exist -> physical instance may exist
CAD_TRANSFER + FAILED   -> ManufacturingRecord blocked    -> physical instance cannot be registered normally
```

## Build / Reuse

No external dependency was added.

Existing lifecycle services are reused for canonical revision-level events:

- installation -> `InstallationService`;
- test -> `TestService`;
- failure -> `FailureService`.

The new physical event stream adds only the missing real-item semantics and does not duplicate canonical serialization.

## Acceptance tests

Pass 3 adds deterministic tests for:

- full instance lifecycle;
- exact instance/revision/manufacturing linkage;
- test activation gate;
- failure evidence retention;
- removal and replacement;
- position occupancy;
- invalid transition rejection;
- monotonic chronology;
- canonical adapter non-regression.

## Known limitations

- storage is still in-memory;
- no removal/replacement event exists in shared `LifecycleEvent v1`;
- no persistence transaction boundary yet exists across canonical + physical event append;
- no concurrency control for simultaneous installations;
- no AI/semantic analysis;
- no field-device integration.

These are explicit future concerns and are not hidden by Pass 3.
