# ORCHESTRATOR HANDOFF — Chat 2

**Pass:** 4  
**Branch:** `chat-2/pass-4`  
**Baseline:** tested Round-3 integration candidate `199cf5a15a22a6b6a01b54540f5f856a18ca7752`  
**Executable implementation SHA:** `dc4968c2e60e515e95d8f2696a36c3121281b4ae`  
**Implementation report SHA:** `ed78a67370dc1de294b7a2010a822dbdcd52da58`  
**Implementation CI:** `MREA CI` run `36643379874` / run #271  
**Date:** 2026-09-30  
**From:** Chat 2 — Physical Measurement  
**To:** Chat 6 / integration review

> This handoff is the final worker commit for this Pass-4 slice. The branch is frozen after this file update. No later worker commit should be added until integration review returns an explicit fix request.

## Why this branch starts from the Round-3 candidate

At Pass-4 start, repository `main` had post-merge orchestration/golden-path work but had not yet received the exact Round-3 worker directory trees. The authoritative tested Round-3 candidate was:

`199cf5a15a22a6b6a01b54540f5f856a18ca7752`

with complete green Round-3 integration evidence. `chat-2/pass-4` was therefore created directly from that exact SHA to avoid regressing Chat-2 Pass-3 content.

## Delivered functionality

Pass 4 closes the measurement-unit truth defect in Chat 2.

Before this pass, `MeasurementSessionService.add_candidate()` hard-coded every candidate as:

```text
unit = mm
```

including `MeasurementType.ANGLE`.

Pass 4 adds `MeasurementTypeRegistry` as the single Chat-2 source of measurement-type unit semantics:

- `ANGLE` -> `deg`;
- every current length-like v1 measurement type -> `mm`.

The service now asks the registry for the unit instead of hard-coding `mm`.

## Fail-closed behavior

`MeasurementTypeRegistry.validate_complete()` compares the registry keys with the complete `MeasurementType` enum. If a future enum member is added without registry semantics, service construction fails instead of silently assigning a wrong unit.

## Canonical boundary

No canonical contract change was required.

The existing `CanonicalMeasurementAdapter` already serializes the internal `measurement.unit`. After this pass, a confirmed angle reaches the canonical wire boundary as:

```text
type = ANGLE
unit = deg
verified = true
confirmation_source = USER_CONFIRMED
```

Existing invariants remain unchanged:

- raw anchors stay `IMAGE_PX`;
- evidence/reference/view linkage is preserved;
- manual/voice/OCR/device values remain candidates until explicit confirmation;
- no geometry normalization moved into Chat 2.

## Files changed in Pass 4

Added:

- `src/physical_measurement/type_registry.py`
- `tests/test_pass4_type_registry.py`
- `docs/PASS_4_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_4.md`

Modified:

- `src/physical_measurement/service.py`
- `src/physical_measurement/__init__.py`
- `ORCHESTRATOR_HANDOFF.md`

No file outside `chat_2_physical_measurement/` was modified.

## Build / Reuse

Recorded in:

`docs/PASS_4_BUILD_REUSE_CHECK.md`

Decision: no third-party units framework. This is a closed MREA domain mapping, not a conversion problem. Python standard library plus the existing canonical `MeasurementType` enum is sufficient.

## Tests added

`tests/test_pass4_type_registry.py` verifies:

1. registry covers every declared measurement type;
2. `ANGLE` maps to `deg`;
3. all current non-angle v1 measurement types map to `mm`;
4. application service assigns the correct unit;
5. a verified angle serializes through the real canonical adapter with `unit = deg`.

## GitHub Actions evidence

Executable implementation state:

```text
run_id = 36643379874
run_number = 271
head_sha = dc4968c2e60e515e95d8f2696a36c3121281b4ae
```

Required Chat-2 gates executed successfully:

- `Chat 2 / Measurement` — `success`;
- `Contracts / canonical fixtures` — `success`;
- `Integration / Chat 1 -> Chat 2` — `success`;
- `Integration / Chat 2 -> Chat 3` — `success`.

Other cross-slice/golden jobs that are not selected for a Chat-2 worker push may remain skipped by repository CI conditions and are not used as Pass-4 acceptance evidence.

## Known limitations / next debt

- internal uncertainty field is still named `uncertainty_mm`; unit-neutral uncertainty remains future work;
- internal `PhysicalMeasurement` still owns exactly two anchors while canonical v1 permits one to three;
- angle-specific geometric/anchor semantics are not implemented here; this pass fixes unit truth only;
- snapping / feature detection remains future work.

## Requested integration review

Verify:

1. all 11 current `MeasurementType` values are registered;
2. `ANGLE` produces `deg` and length-like values remain `mm`;
3. no existing manual/hands-free provenance or confirmation rule regressed;
4. canonical adapter emits the correct angle unit without contract changes;
5. Chat-2 and both adjacent integration gates remain green;
6. worker ownership is respected.

If accepted, integrate this slice onto the post-Round-3 accepted baseline. This branch is frozen after the handoff commit.
