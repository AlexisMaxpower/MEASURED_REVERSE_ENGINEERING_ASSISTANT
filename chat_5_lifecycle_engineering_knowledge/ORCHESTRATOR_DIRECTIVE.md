# ORCHESTRATOR DIRECTIVE — Chat 5
**Revision:** OD-2026-09-29-002  
**Owner:** Chat 6
**Pass:** 2  
**Branch:** `chat-5/pass-2`

## Accepted from Pass 1
Canonical thin `LifecycleEvent v1` adapter and internal revision/manufacturing/install/failure baseline are accepted. Pass-1 process defect: no `ORCHESTRATOR_HANDOFF.md` was published.

## Pass 2 priority
Link CAD verification outcome to lifecycle/manufacturing eligibility without importing CAD vendor details into the lifecycle domain.

Required:
- define a slice-local input adapter/policy consuming canonical CAD verification result;
- verified CAD transfer may permit revision/manufacturing progression;
- FAILED/MISMATCH/MISSING/CONSTRAINT_CONFLICT must not silently permit manufacturing eligibility;
- preserve lifecycle evidence and event ordering;
- keep the shared `LifecycleEvent v1` thin and unchanged unless a Change Request is approved;
- add explicit tests for accepted and rejected verification states.

## CI requirement
Push Pass 2 only to `chat-5/pass-2`. GitHub-hosted Chat 5 tests must remain green. As the Chat 4 → Chat 5 boundary becomes executable, a repository-level integration test will be added by Chat 6 or by explicit directive. Record CI status in `ORCHESTRATOR_HANDOFF.md`.

## Do not
- import SOLIDWORKS-specific types;
- edit shared contracts directly;
- treat a failed CAD verification as manufacturable;
- add AI before structured lifecycle/eligibility behavior is stable;
- commit Pass 2 implementation directly to `main`.

## Mandatory handoff
Finish Pass 2 with `ORCHESTRATOR_HANDOFF.md` per `chat_6_orchestrator/DEVELOPMENT_WORKFLOW.md`.
