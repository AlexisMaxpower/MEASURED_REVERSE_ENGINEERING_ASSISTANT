# ORCHESTRATOR HANDOFF — Chat 5 / Pass 3

**Directive:** `OD-2026-09-29-003`  
**Branch:** `chat-5/pass-3`  
**Accepted base SHA:** `c3452d7fa68c9c5c3716db5fef71172e9c3b9532`  
**Independently tested implementation SHA:** `f92bc1aeea7df601c43080ed6eb78bb18b608571`  
**CI run:** `36619302842`  
**Status at handoff:** required Chat 5 gates GREEN

> This handoff is the final worker commit and freezes `chat-5/pass-3`. A Git commit cannot contain its own SHA. Chat 6 must use the current `chat-5/pass-3` branch head as the final handoff commit and the SHA above as the exact implementation state independently exercised by CI immediately before the handoff.

## 1. Delivered functionality

Pass 3 extends Chat 5 from revision/manufacturing history to the real-world lifecycle of one concrete manufactured item.

Implemented:

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

### Physical manufactured identity

Added `PhysicalPartInstance` tied to exactly one existing `ManufacturingRecord` and therefore to exactly one Revision.

The identity retains:

- `instance_id`;
- `part_id`;
- `revision_id`;
- `manufacturing_id`;
- material;
- manufacturing method;
- manufacturing timestamp;
- batch/machine/print-profile snapshot when available.

A physical instance cannot be registered without a previously accepted manufacturing record.

### Deterministic physical state machine

Internal states:

```text
MANUFACTURED
INSTALLED
TESTED
ACTIVE
FAILED
REMOVED
SUPERSEDED
```

Normal path:

```text
MANUFACTURED → INSTALLED → TESTED → ACTIVE
```

Failure/replacement path:

```text
INSTALLED / TESTED / ACTIVE
→ FAILED
→ REMOVED
→ SUPERSEDED
```

Preventive replacement is also allowed from installed/tested/active through explicit removal before supersession.

Invalid transitions fail closed.

### Explicit test gate

A physical test carries internal `PhysicalTestOutcome`:

- `PASSED`;
- `FAILED`.

Activation is allowed only when the latest physical event is a test with outcome `PASSED`. Free-text `TestRecord.result` is not parsed as lifecycle truth.

### Equipment / position occupancy

`PhysicalEquipmentRegistry` derives the current physical occupant for `equipment_id + position`.

The following states continue to occupy the location:

- `INSTALLED`;
- `TESTED`;
- `ACTIVE`;
- `FAILED`.

A failed item still occupies the location until an explicit `REMOVED` transition.

A second instance cannot be installed into an occupied equipment/position.

### Failure evidence and exact item linkage

`Installation`, `TestRecord`, and `FailureRecord` now support optional `instance_id` for backward compatibility.

The Pass 3 physical path requires the identity and validates that:

- revision matches the instance;
- manufacturing record matches the instance;
- test/failure installation matches the instance's current installation;
- failure evidence remains on the exact `FailureRecord` and is traceable to the exact `instance_id` and revision.

### Removal and replacement

`REMOVED` releases equipment/position occupancy.

`SUPERSEDED` requires:

- old instance already `REMOVED`;
- replacement is a different instance;
- replacement belongs to the same part;
- replacement is installed/tested/active;
- replacement occupies the same equipment/position;
- chronology remains monotonic.

The superseded event retains `replacement_instance_id`.

## 2. Canonical inputs / outputs used

Consumed without modification:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- canonical CAD fixtures already used by the accepted Pass 2 boundary;
- canonical `LifecycleEvent v1` contract.

Shared output remains unchanged:

```text
mrea.lifecycle-event.v1
REVISION_CREATED
MANUFACTURED
INSTALLED
TESTED
FAILED
```

Physical-only facts such as:

- `instance_id`;
- `ACTIVATED`;
- `REMOVED`;
- `SUPERSEDED`;
- `replacement_instance_id`;
- explicit physical test outcome;

remain Chat-5-internal and are not emitted as new shared lifecycle event types.

No Change Request was needed for Pass 3.

## 3. CAD manufacturing eligibility invariant

Pass 2 eligibility is preserved.

The physical service never creates or bypasses a `ManufacturingRecord`. It can register an instance only from an already existing manufacturing record.

Therefore:

```text
CAD_TRANSFER + VERIFIED → ManufacturingRecord may exist → physical instance may exist
CAD_TRANSFER + FAILED   → manufacturing blocked → physical instance cannot enter normal lifecycle
```

No override mechanism was added.

## 4. Files changed in Pass 3

Modified:

- `README.md`
- `docs/IMPLEMENTATION_STATE.md`
- `src/mrea_lifecycle/__init__.py`
- `src/mrea_lifecycle/models.py`
- `src/mrea_lifecycle/store.py`
- `ORCHESTRATOR_HANDOFF.md` — this final freeze commit

Added:

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `src/mrea_lifecycle/physical.py`
- `tests/test_physical_instance_lifecycle.py`

No files outside `chat_5_lifecycle_engineering_knowledge/` were modified by Chat 5.

## 5. Test inventory added

`tests/test_physical_instance_lifecycle.py` covers:

1. manufacturing record → concrete physical instance;
2. revision/manufacturing/material/method identity retention;
3. installation with equipment/position;
4. explicit physical test outcome;
5. successful test → activation;
6. exact failure instance/revision/evidence traceability;
7. failure → removal;
8. old instance removal releases location;
9. replacement instance installation at same location;
10. replacement activation;
11. removed old instance → superseded by exact replacement;
12. deterministic physical timeline;
13. canonical lifecycle export remains thin and contains no `instance_id`;
14. activation before test rejected;
15. failed test cannot activate;
16. backward-time transition rejected;
17. installation into occupied equipment/position rejected without canonical installation mutation;
18. supersession before removal rejected.

Existing Pass 1/2 tests remain in the same suite.

## 6. Tests actually executed

### Independent GitHub-hosted Chat 5 suite

Workflow run:

```text
MREA CI / 36619302842
head: f92bc1aeea7df601c43080ed6eb78bb18b608571
job: Chat 5 / Lifecycle
```

Exact result:

```text
15 passed in 0.07s
```

Result: **SUCCESS**, with no pytest collection warning from Chat 5 after the final test-import cleanup.

### Canonical contract / fixture gate

Same workflow run:

```text
Contracts / canonical fixtures
```

Result: **SUCCESS**.

### Real Chat 4 → Chat 5 integration gate

Same workflow run:

```text
Integration / Chat 4 -> Chat 5
```

Exact result:

```text
2 passed, 1 warning in 0.46s
```

Result: **SUCCESS**.

The single warning originates in Chat 4's existing `TestDoubleCadAdapter` pytest collection naming and is outside Chat 5 ownership. It does not indicate a failed boundary test and was not modified by Chat 5.

## 7. CI status known at handoff time

Required Pass 3 gates for Chat 5 on tested implementation SHA:

- `Chat 5 / Lifecycle` — **SUCCESS**;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**;
- Chat 4 generic prerequisite in the same run — **SUCCESS**.

No required Chat 5 CI job is red at handoff time.

Per Pass 3 workflow, this handoff commit now freezes the branch. Any CI generated by the handoff commit itself is post-handoff evidence for Chat 6 to record centrally; Chat 5 will not move the branch merely to update that result.

## 8. Tests not executed / external gates

No physical database, REST API, concurrent writer, field-device, or migration tests were executed because those capabilities are not implemented in Pass 3.

No real SOLIDWORKS runtime test is owned by Chat 5. The Chat 4 → Chat 5 software boundary was executed through the repository integration gate and passed.

## 9. Build / Reuse decision

No new external dependency was introduced.

Pass 3 reuses:

- `InMemoryLifecycleStore`;
- `ManufacturingService` and its CAD eligibility rule;
- `InstallationService`;
- `TestService`;
- `FailureService`;
- `CanonicalLifecycleEventAdapter`.

The new physical event stream exists only for semantics absent from shared `LifecycleEvent v1`; canonical serialization was not duplicated or redefined.

## 10. Known limitations

Still intentionally not implemented:

- production persistence;
- repository abstraction / transaction boundary across canonical + physical events;
- concurrent installation conflict control beyond deterministic in-memory checks;
- REST/API;
- database migrations;
- field-device integration;
- AI / semantic failure analysis;
- shared physical-instance event contract.

The in-memory application path validates event IDs before canonical/physical paired writes where applicable, but a real atomic transaction boundary belongs to future persistence work.

## 11. Open Change Requests

None from Chat 5 for Pass 3.

The shared v1 lifecycle contract is sufficient because physical-instance-only states remain internal in this pass.

## 12. Ownership verification

Pre-handoff diff against accepted base `c3452d7fa68c9c5c3716db5fef71172e9c3b9532` contained exactly eight implementation/documentation files, all under Chat 5 ownership.

This handoff adds only the ninth changed file, `ORCHESTRATOR_HANDOFF.md`.

No changes were made to:

- `core/contracts/`;
- canonical fixtures;
- `.github/workflows/`;
- `tests/integration/`;
- Chat 1–4;
- Chat 6 documentation.

## 13. Requested acceptance gate

Please verify:

1. concrete physical identity is tied to exact revision + manufacturing record;
2. lifecycle transitions are deterministic and invalid transitions fail closed;
3. equipment/position occupancy cannot silently contain two physical instances;
4. test pass is explicit before activation;
5. failure evidence is linked to exact physical instance and revision;
6. removal/replacement/supersession remain auditable;
7. failed/unverified CAD still cannot bypass manufacturing;
8. canonical `LifecycleEvent v1` remains unchanged;
9. required CI gates are green;
10. ownership boundaries are preserved.

Requested verdict: **Pass 3 ACCEPTED or explicit FIX_REQUIRED directive.**
