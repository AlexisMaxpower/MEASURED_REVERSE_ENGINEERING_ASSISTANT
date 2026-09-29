# ROUND 3 — Finding 002 Final Review Request

**From:** Chat 7 — Deputy Orchestrator 1  
**To:** Chat 8 — Deputy Orchestrator 2 / Final Review  
**Status:** `READY_FOR_REPEATED_FINAL_REVIEW`

## Exact candidate under review

- branch: `integration/pass-3-candidate`
- candidate SHA: `1c9ccb432664e57a24be8fe586bb07ad13fd5075`
- candidate tree: `435dda140d3980256ca32c42bd07d81b15c4328c`
- direct parent / current main: `dcdb1b7a1399415522a1a17a7979dda536f116f4`
- PR: `#27`

Do not review or merge the superseded candidate `199cf5a15a22a6b6a01b54540f5f856a18ca7752`.

## Authoritative CI evidence

MREA CI push run:

`36644505122`

Result:

`SUCCESS`

Actually executed + SUCCESS:

- Contracts / canonical fixtures
- Chat 1 / Capture
- Chat 2 / Measurement
- Chat 3 / Geometry
- Chat 4 / Generic CAD gate
- Chat 5 / Lifecycle
- Integration / Chat 1 -> Chat 2
- Integration / Chat 2 -> Chat 3
- Integration / Chat 3 -> Chat 4
- Integration / Chat 4 -> Chat 5
- Integration / Round 3 golden path

Golden step:

`Run Round 3 Capture -> Physical Instance golden path` — `SUCCESS`

No required boundary or golden gate is represented by `skipped`.

## Finding 002 state presented to Final Review

The shared workflow correction is inherited from current main and enables the Round-3 golden job on `main` as well as integration candidates.

Pre-merge main run `36643094207` executed the newly enabled golden job but failed because pre-merge main does not contain the Round-3 golden test/worker tree. No fake skip, placeholder, or weaker substitute was introduced.

The rebuilt candidate is based directly on that corrected main and is fully green.

Chat 7 does **not** claim Finding 002 closed. Final Review must decide whether this sequence satisfies the pre-merge requirement and, if accepted, authorize the exact candidate for merge.

## Required Chat 8 actions

1. independently verify candidate parent, tree, and frozen worker provenance;
2. independently verify CI run `36644505122` is for exact SHA `1c9ccb432664e57a24be8fe586bb07ad13fd5075`;
3. verify all 5 slice jobs, contracts, 4 boundary jobs, and golden job actually executed and succeeded;
4. verify no Pass-4+ worker content entered Round 3;
5. decide Finding 002 / Final Review outcome;
6. if accepted, authorize merge of the **exact** candidate SHA above;
7. after merge, require a full `main` CI run where `Integration / Round 3 golden path` actually executes and succeeds;
8. close Round 3 only after that post-merge evidence exists.

## External gate

```text
REAL SOLIDWORKS 2026 HOST = EXTERNAL_GATE_UNVERIFIED
```

No Linux/TestDouble evidence should be interpreted as real-host SOLIDWORKS verification.