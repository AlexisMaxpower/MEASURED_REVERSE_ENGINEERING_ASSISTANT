# Chat 4 — Pass 3 Primary Progress

**Directive:** `OD-2026-09-29-003`  
**Primary branch:** `chat-4/pass-3`  
**Baseline main:** `c3452d7fa68c9c5c3716db5fef71172e9c3b9532`  
**Side branch:** `chat-4b/pass-3`  
**State:** PRIMARY HALF IMPLEMENTED; SIDE CHAT 4B INTEGRATION PENDING

This file is progress state only. It is **not** the final `ORCHESTRATOR_HANDOFF.md` and does not freeze the branch.

## Primary Chat 4 delivered

- slice-local `mrea.cad-host-readiness.v1` model;
- deterministic readiness aggregation (`READY / FAILED / UNVERIFIED`);
- parser that rejects producer-claimed READY when checks disagree;
- machine-readable `CadRuntimeEvidenceError` and diagnostics;
- slice-local `mrea.cad-runtime-evidence.v1` builder;
- fail-closed separation between numerical CAD verification and actual real-host verification;
- identity consistency checks across SketchPackage/CADPackage/adapter/verification report;
- artifact consistency and SHA-256 evidence requirement;
- read-back versus verification-report consistency checks;
- dedicated Side Chat 4B Pass 3 task specification.

## Local verification

Targeted pure runtime-evidence tests in the ChatGPT sandbox:

```text
14 tests
OK
```

The tests cover:

- readiness aggregation;
- fail precedence;
- machine-readable failure code propagation;
- readiness status recomputation;
- false READY rejection;
- diagnostic parsing;
- TEST_DOUBLE/numerical success remaining real-host UNVERIFIED;
- missing SOLIDWORKS version fail-closed;
- missing native SHA-256 fail-closed;
- full real-host evidence eligibility;
- numerical mismatch remains FAILED;
- SketchPackage identity mismatch rejection;
- read-back/report drift rejection;
- adapter-result/CADPackage artifact drift rejection.

## Repository CI evidence

CI run `36618497589` on primary Pass 3 content established:

- Chat 4 / Generic CAD gate — **PASS**;
- Contracts / canonical fixtures — **PASS**;
- Chat 4 -> Chat 5 integration — **PASS**;
- Chat 1/2/3/5 slice suites — **PASS**;
- Chat 3 -> Chat 4 integration — **FAIL**, caused by an Integrator-owned test defect, not Chat 4 production output.

The failing integration test indexes:

```python
transfer.cad_verification_report["dimensions"]
```

while canonical `CADVerificationReport v1` defines `items`. The exact blocker and requested one-line Integrator fix are documented in:

`docs/INTEGRATOR_BLOCKER_CHAT3_TO_CHAT4_CI_PASS3.md`

Primary Chat 4 deliberately does not add a non-canonical `dimensions` field to work around the faulty assertion.

## Side Chat 4B pending work

See `docs/SIDE_CHAT_4B_PASS_3_TASK.md`.

Side 4B owns actual:

- Windows/x64 probing;
- .NET/SOLIDWORKS prerequisites;
- COM/version/interop probing;
- writable output/template probing;
- stable process exit codes;
- one-command golden host procedure;
- real host facts/artifact/read-back production.

The side branch `chat-4b/pass-3` has been created from the same accepted baseline and contains the runtime-evidence specification plus its assigned Pass 3 task.

## Runtime status

Actual Windows 11 + SOLIDWORKS 2026 execution is still:

`UNVERIFIED`

No runtime PASS is claimed.

## Next primary action

After Side Chat 4B publishes `SOLIDWORKS_SIDE_HANDOFF.md` and Chat 6 resolves the integration-test blocker:

1. review Side Chat 4B branch diff;
2. integrate only owned vendor changes;
3. connect host-readiness payload to the Primary evidence parser;
4. run complete Chat 4 regression;
5. rerun Chat 3 -> Chat 4 and Chat 4 -> Chat 5 gates;
6. update final `ORCHESTRATOR_HANDOFF.md` once;
7. freeze branch for Chat 6 review.
