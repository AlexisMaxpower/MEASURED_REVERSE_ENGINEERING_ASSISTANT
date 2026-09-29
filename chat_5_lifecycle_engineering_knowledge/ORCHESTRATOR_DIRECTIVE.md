# ORCHESTRATOR DIRECTIVE — Chat 5
**Revision:** OD-2026-09-29-002  
**Pass:** 2  
**Owner:** Chat 6  
**Round 1 verdict:** ACCEPTED WITH PROCESS FIX

Read before Pass 2 implementation.

## Branch policy

Pass 2 work MUST be performed on:

`chat-5/pass-2`

Do not commit Pass 2 implementation directly to `main`.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/cad_package_v1.json`
- `tests/fixtures/contracts/cad_verification_v1.json`
- `tests/fixtures/contracts/lifecycle_event_v1.json`

## Accepted baseline

OD-001 canonical LifecycleEvent adapter is accepted. Rich revision/manufacturing/install/test/failure state remains internal to Chat 5.

Process correction: Pass 1 did not publish `ORCHESTRATOR_HANDOFF.md`. From Pass 2 onward this file is mandatory.

## Pass 2 priority — CAD verification → lifecycle linkage

Close the currently missing Chat 4 → Chat 5 product boundary.

Implement an application/domain path that can create or prepare a lifecycle Revision from canonical CAD outputs while retaining traceability.

At minimum preserve internally:

- `cad_package_id`;
- `sketch_package_id`;
- `cad_verification_report_id`;
- native/output artifact references available from CADPackage;
- verification status used for lifecycle eligibility.

## Manufacturing eligibility rule

For the normal v1 path:

- `CADVerificationReport.overall_status == VERIFIED` may make a revision eligible for manufacturing;
- failed/missing/unverified CAD transfer must NOT silently become manufacturing-ready;
- if an override mechanism is introduced, it must be explicit, auditable and separate from VERIFIED status. Do not invent a silent boolean bypass.

No shared LifecycleEvent contract change is required just to store this richer linkage internally.

## Required tests

Cover at least:

1. VERIFIED CAD report → revision may progress to manufacturing;
2. FAILED report → manufacturing path rejected/blocked;
3. mismatched CADPackage/report linkage rejected;
4. CAD IDs/artifact traceability retained on revision/internal record;
5. existing canonical LifecycleEvent export remains unchanged/green.

## Scope control

Do not start AI/semantic search in this pass.

Do not build production database persistence before the CAD→Lifecycle integration gate is green unless required for a minimal repository abstraction test.

## Acceptance target

Demonstrate:

```text
canonical CADPackage
+ canonical CADVerificationReport
→ lifecycle revision linkage
→ VERIFIED manufacturing eligibility
→ existing lifecycle event flow
```

with explicit rejection of failed/unverified CAD transfer.

## Required handoff

Create/update `ORCHESTRATOR_HANDOFF.md` with Pass 2 branch, final SHA, exact tests executed, limitations and requested acceptance gate.
