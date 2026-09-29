# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-29**
- Branch: `chat-5/pass-3`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Orchestrator directive: **OD-2026-09-29-003**
- Accepted baseline: **Pass 2 ACCEPTED**
- State: **Pass 3 physical part instance lifecycle implemented; acceptance pending CI/handoff**

## Accepted baseline

Still active and unchanged:

- Revision / Manufacturing / Installation / Test / Failure domain;
- CAD-linked Revision preparation;
- CAD verification manufacturing eligibility gate;
- canonical `LifecycleEvent v1` outbound adapter;
- revision-level timeline/state/comparison/knowledge queries;
- real Chat 4 -> Chat 5 boundary gate.

Pass 2 independent CI was green before Pass 3 began, including:
- `Contracts / canonical fixtures`;
- `Chat 5 / Lifecycle`;
- `Integration / Chat 4 -> Chat 5`.

## Pass 3 additions

### Physical identity

`PhysicalPartInstance` is a slice-local identity for one real manufactured item.

It retains:
- `instance_id`;
- `part_id`;
- `revision_id`;
- `manufacturing_id`;
- material;
- manufacturing method;
- manufactured timestamp;
- batch/machine/print profile snapshot where available.

A physical instance can only be registered from an existing `ManufacturingRecord`, so a failed/unverified CAD revision still cannot bypass the existing manufacturing eligibility gate.

### Internal physical state machine

States:

```text
MANUFACTURED
INSTALLED
TESTED
ACTIVE
FAILED
REMOVED
SUPERSEDED
```

Normal progression:

```text
MANUFACTURED -> INSTALLED -> TESTED -> ACTIVE
```

Supported service exits:

```text
INSTALLED / TESTED / ACTIVE -> FAILED -> REMOVED -> SUPERSEDED
INSTALLED / TESTED / ACTIVE -> REMOVED -> SUPERSEDED
```

Rules are fail-closed:
- activation requires the latest physical test to be explicitly `PASSED`;
- timestamps cannot move backward for one physical instance;
- a physical installation must carry non-empty equipment/position;
- one equipment/position cannot contain two non-removed physical instances;
- supersession requires the old instance to be `REMOVED`;
- replacement must be a different instance of the same part;
- replacement must occupy the same equipment/position.

### Exact evidence linkage

`Installation`, `TestRecord`, and `FailureRecord` now support optional `instance_id`.

The Pass 3 physical path requires this identity and checks:
- revision equality;
- manufacturing equality;
- installation equality for tests/failures;
- failure evidence remains attached to the exact `FailureRecord` and exact physical instance.

Legacy revision-level callers remain compatible because `instance_id` is optional outside the physical-instance application path.

### Physical event stream

Added internal `PhysicalLifecycleEvent` and `PhysicalLifecycleEventType`.

Physical events are independent from shared `LifecycleEvent v1` and include:
- concrete `instance_id`;
- revision/manufacturing identity;
- installation/test/failure references;
- equipment/position context;
- explicit test outcome;
- replacement instance identity for supersession.

This avoids changing the Chat-6-owned shared lifecycle contract merely to represent internal real-world states.

### Projections

Added:
- `PhysicalPartTimeline`;
- `PhysicalPartStateProjection`;
- `PhysicalEquipmentRegistry`;
- `PhysicalPartLifecycleService`.

## Shared contract compatibility

No shared contract or canonical fixture was changed.

Canonical lifecycle export remains limited to:

```text
REVISION_CREATED
MANUFACTURED
INSTALLED
TESTED
FAILED
```

Internal states/events such as `ACTIVATED`, `REMOVED`, and `SUPERSEDED` are not exported as canonical `LifecycleEvent v1`.

## Build / Reuse decision

No new dependency was added.

Pass 3 deliberately reuses:
- existing `InMemoryLifecycleStore`;
- existing `InstallationService`;
- existing `TestService`;
- existing `FailureService`;
- existing `ManufacturingService` eligibility invariant;
- existing canonical lifecycle adapter.

A separate physical-instance service/state machine was added only for behavior not represented by the shared v1 contract.

## New deterministic tests

`tests/test_physical_instance_lifecycle.py` covers:

1. manufacturing record -> physical instance identity;
2. install -> test -> active;
3. failure with exact instance/revision/evidence linkage;
4. removal;
5. replacement/supersession by a new instance;
6. equipment/position registry update;
7. canonical export remaining thin;
8. activation before test rejected;
9. failed test cannot activate;
10. backward-time transition rejected;
11. occupied equipment/position rejected without partial canonical mutation;
12. supersession before removal rejected.

## Files added in Pass 3

- `src/mrea_lifecycle/physical.py`;
- `tests/test_physical_instance_lifecycle.py`;
- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`.

## Files modified in Pass 3

- `src/mrea_lifecycle/models.py`;
- `src/mrea_lifecycle/store.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Not implemented

- production persistence;
- repository abstraction;
- REST/API;
- concurrency/versioning;
- migrations;
- AI / semantic failure analysis;
- shared physical-instance event contract.

## Acceptance gate

Before handoff:
- Chat 5 suite must be green;
- canonical contract job must remain green;
- real `Integration / Chat 4 -> Chat 5` must remain green.

Handoff then freezes `chat-5/pass-3`.
