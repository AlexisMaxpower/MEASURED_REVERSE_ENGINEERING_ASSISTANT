# MREA Orchestration State

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive revision:** `OD-2026-09-30-004`  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** `ROUND_4_BLOCKED_BY_CHAT3_CHAT5_FIX_REQUIRED`

## Final Review finding

Chat 8 returned:

`FINAL_REVIEW_FIX_REQUIRED`

Finding:

`chat_8_deputy_orchestrator/ROUND_4_FINAL_REVIEW_FINDING_001_CROSS_SLICE_COVERAGE.md`

Chat 6 accepted the finding and added Round-4-specific shared boundary/golden-path coverage.

## Corrected shared infrastructure

Shared code/CI baseline before the control-document commit containing this state:

```text
main: 6157c7154e3cd08d3e4d60b05c65b5445888ba24
tree: 0cb7b15abb1553654f009be6dbbe73029e046a88
```

Evidence:

```text
36751841476  MREA Round 4 Truth CI  SUCCESS
36751841522  MREA CI                SUCCESS
```

Added shared gates:

- `tests/integration/test_round4_chat1_to_chat2_truth.py`
- `tests/integration/test_round4_chat2_to_chat3_truth.py`
- `tests/integration/test_round4_chat3_to_chat4_truth.py`
- `tests/integration/test_round4_chat4_to_chat5_truth.py`
- `tests/integration/test_round4_golden_path.py`
- `.github/workflows/round4_truth.yml`

## Diagnostic replay candidate

Same accepted Round-4 worker replay content was rebuilt over corrected main:

```text
branch: integration/pass-4-candidate
base:   6157c7154e3cd08d3e4d60b05c65b5445888ba24
SHA:    b5fdcd6324efd1396a3d57a28fc11e0dd0ba4afd
tree:   feaa4de6f84bda514e92d5bbf9939f1187da35a3
```

Regression:

`36752208418` — `MREA CI` — `SUCCESS`

Round-4 truth:

`36752208521` — `FAILURE`

The candidate is diagnostic evidence only and is not authorized for merge/final acceptance.

## Boundary results

```text
Round 4 Chat 1 -> Chat 2 truth  SUCCESS
Round 4 Chat 2 -> Chat 3 truth  FAILURE
Round 4 Chat 3 -> Chat 4 truth  SUCCESS
Round 4 Chat 4 -> Chat 5 truth  FAILURE
Round 4 golden path             SKIPPED (blocked by failed dependencies)
```

## Confirmed blocker A — Chat 3

Canonical physical uncertainty from Chat 2 is silently lost by Chat 3 normalization/binding.

Observed failure:

```text
MeasurementPackage uncertainty = 0.5
MeasurementRef has no uncertainty
```

Action:

`chat_3_geometry_semi_automatic_sketch/ORCHESTRATOR_FIX_REQUIRED_ROUND4_001.md`

`chat-3/pass-8` is explicitly reopened only for that correction.

## Confirmed blocker B — Chat 5

Chat 5 cannot consume Chat-4 runtime evidence/status.

Observed failure:

```text
CADRevisionPreparationService.prepare()
got an unexpected keyword argument 'runtime_evidence'
```

Therefore runtime `UNVERIFIED` cannot currently be persisted/enforced as a manufacturing blocker for runtime-gated CAD origins.

Action:

`chat_5_lifecycle_engineering_knowledge/ORCHESTRATOR_FIX_REQUIRED_ROUND4_001.md`

`chat-5/pass-8` is explicitly reopened only for that correction.

## Frozen slices not reopened

```text
Chat 1  chat-1/pass-4 @ a7d607f8cdd281749ae40529de15c2d84dfda78e  ACCEPTED / FROZEN
Chat 2  chat-2/pass-6 @ 539d58567046fd29ccf2d42b629227ffe8da6546  ACCEPTED / FROZEN
Chat 4  chat-4/pass-7 @ 61f37a4dd46921b7fe9145bcbe5242bc3f6417b3  ACCEPTED / FROZEN
```

Chat 3 previous frozen handoff:

`d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`

Chat 5 previous frozen handoff:

`82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`

## Next state transition

```text
CHAT3_FIX_REQUIRED + CHAT5_FIX_REQUIRED
    -> corrected worker re-handoffs
    -> Chat6 independent review
    -> replay corrected Chat3/Chat5 slice content over current shared main
    -> MREA CI SUCCESS
    -> all Round4 Truth boundary jobs SUCCESS
    -> Round4 golden path ACTUALLY EXECUTED + SUCCESS
    -> new exact candidate to Chat8
    -> Chat8 Final Review
```

No merge to main is authorized before Chat 8 returns an exact-SHA acceptance verdict.

## External environment truth

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```
