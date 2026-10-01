# Chat 2 — Pass 4 Implementation Report

## Baseline

Pass 4 was branched from the exact tested Round-3 integration candidate:

`199cf5a15a22a6b6a01b54540f5f856a18ca7752`

Reason: at branch creation time current `main` had not yet received the accepted Round-3 worker directory trees, while candidate `199cf5a...` had complete green integration evidence.

## Problem closed

`MeasurementSessionService.add_candidate()` previously hard-coded:

```python
unit="mm"
```

for every `MeasurementType`, including `ANGLE`.

That contradicted canonical v1 semantics where length-like values use `mm` and angular values use `deg`.

## Implementation

Added:

- `MeasurementTypeSemantics` — immutable domain semantics record;
- `MeasurementTypeRegistry` — complete registry for all 11 canonical measurement types;
- fail-closed `validate_complete()` guard against future enum/registry drift.

Updated `MeasurementSessionService`:

- accepts an optional registry dependency;
- validates registry completeness at service construction;
- derives candidate unit from `MeasurementTypeRegistry.unit_for()` instead of hard-coding `mm`.

Current v1 mapping:

- `ANGLE` -> `deg`;
- all other current measurement types -> `mm`.

No unit conversion is performed. The registry only owns type semantics.

## Boundary behavior

The canonical adapter did not require modification. It already serializes the internal measurement `unit` value. Therefore an explicitly confirmed `ANGLE` candidate now reaches the wire boundary with:

```text
type = ANGLE
unit = deg
verified = true
confirmation_source = USER_CONFIRMED
```

Raw anchors remain `IMAGE_PX` and all existing evidence/provenance behavior is preserved.

## Tests

Added `tests/test_pass4_type_registry.py` covering:

1. registry completeness for every declared `MeasurementType`;
2. `ANGLE -> deg`;
3. all current length-like types -> `mm`;
4. service-level unit assignment;
5. canonical adapter serialization of a verified angle as `deg`.

GitHub Actions implementation run:

`36643379874` / run `271`

Relevant results:

- `Chat 2 / Measurement` — success;
- `Contracts / canonical fixtures` — success;
- `Integration / Chat 1 -> Chat 2` — success;
- `Integration / Chat 2 -> Chat 3` — success.

## Ownership

Only `chat_2_physical_measurement/` was modified.

No canonical contracts, shared fixtures, Chat-6-owned workflow, shared integration test, geometry code or CAD/lifecycle code was changed.

## Remaining debt

- internal field name `uncertainty_mm` is still length-specific and should later become unit-neutral without breaking compatibility;
- internal model still uses exactly two anchors, while the canonical wire contract allows one to three;
- angle geometry/anchor semantics are not yet specialized; this pass fixes unit truth only;
- no automatic feature anchor snapping was added in this pass.
