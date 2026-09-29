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

## CI

A repository push CI run is triggered for the primary branch. Final Pass 3 handoff must record the completed canonical/generic/integration gates after Side Chat 4B integration.

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

## Runtime status

Actual Windows 11 + SOLIDWORKS 2026 execution is still:

`UNVERIFIED`

No runtime PASS is claimed.

## Next primary action

After Side Chat 4B publishes `SOLIDWORKS_SIDE_HANDOFF.md`:

1. review branch diff;
2. integrate only owned vendor changes;
3. connect host-readiness payload to the Primary evidence parser;
4. run complete Chat 4 regression;
5. verify Chat 3 -> Chat 4 and Chat 4 -> Chat 5 gates;
6. update final `ORCHESTRATOR_HANDOFF.md` once;
7. freeze branch for Chat 6 review.
