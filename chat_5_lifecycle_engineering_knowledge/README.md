# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 3 physical part instance lifecycle implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Текущая директива: **OD-2026-09-29-003**  
Рабочая ветка: `chat-5/pass-3`

## Назначение области

Chat 5 хранит как инженерную историю ревизии, так и фактическую жизнь конкретно изготовленного экземпляра:

```text
Revision
→ ManufacturingRecord
→ PhysicalPartInstance
→ Installed
→ Tested
→ Active / In service
→ Failed
→ Removed
→ Superseded by replacement
```

## Реализовано

### Pass 1

- Revision / Manufacturing / Installation / Test / Failure domain;
- revision-level timeline, registry and projections;
- deterministic knowledge queries;
- canonical `LifecycleEvent v1` outbound adapter.

### Pass 2

- canonical `CADPackage + CADVerificationReport` → lifecycle Revision;
- CAD traceability retention;
- `VERIFIED` manufacturing eligibility gate;
- failed/unverified CAD transfer cannot enter manufacturing.

### Pass 3

Добавлен отдельный internal physical-instance layer:

- `PhysicalPartInstance`;
- `PhysicalPartState`;
- `PhysicalLifecycleEvent`;
- `PhysicalPartLifecycleService`;
- `PhysicalPartTimeline`;
- `PhysicalPartStateProjection`;
- `PhysicalEquipmentRegistry`;
- exact instance linkage on Installation/Test/Failure records;
- explicit `PASSED` test gate before activation;
- removal and replacement/supersession traceability;
- occupied equipment/position protection;
- monotonic instance chronology;
- fail-closed invalid-transition rejection.

## Physical state machine

Normal path:

```text
MANUFACTURED
→ INSTALLED
→ TESTED
→ ACTIVE
```

Service exit paths:

```text
INSTALLED / TESTED / ACTIVE
→ FAILED
→ REMOVED
→ SUPERSEDED

INSTALLED / TESTED / ACTIVE
→ REMOVED
→ SUPERSEDED
```

`SUPERSEDED` requires a different physical instance of the same part to be installed/in service at the same equipment/position.

## Shared-contract boundary

Physical-instance events are intentionally internal in Pass 3.

Canonical `mrea.lifecycle-event.v1` remains unchanged and still exports only:

- `REVISION_CREATED`;
- `MANUFACTURED`;
- `INSTALLED`;
- `TESTED`;
- `FAILED`.

`ACTIVE`, `REMOVED` and `SUPERSEDED` do not leak into the shared v1 contract.

## Verification target

Pass 3 must keep green:

- `Chat 5 / Lifecycle`;
- `Integration / Chat 4 -> Chat 5`;
- canonical contract checks;
- new deterministic physical lifecycle tests.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- AI / semantic failure analysis;
- production persistence;
- REST/API;
- concurrency/versioning;
- shared contract expansion for physical events.
