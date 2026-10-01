# Chat 2 — Pass 17 Implementation Report

## Baseline

Pass 17 starts from accepted cumulative Round-16 `main`:

`933d925c69944d40859ae1f9ff80d7a3ecb7f760`

Directive: `OD-2026-10-02-009`.

Round 16 already contains Chat 2 Pass 15 durable keyset pagination and Pass 16 deterministic spoken measurement parsing/unit validation. Pass 17 does not revive any historical branch.

## Goal

Close the offline-first continuity gap between durable `MeasurementSession` storage and process-local hands-free interaction state.

Before this pass, an unverified candidate survived SQLite reopen, but a new `HandsFreeMeasurementController` always started in `IDLE`; the persisted candidate could not continue through the normal confirm/reject/correct flow without reconstructing state externally.

## Implementation

Added `physical_measurement/recovery.py` with:

- `resume_hands_free_controller(...)`;
- `HandsFreeRecoveryError`;
- `AmbiguousPendingMeasurementRecovery`.

Recovery derives actionable controller state from the existing durable measurement session rather than persisting a second workflow-state payload.

### Exact-context matching

A pending measurement matches the controller only when all of the following agree:

- measurement type;
- view;
- ordered anchors;
- evidence frame;
- instrument type;
- uncertainty.

Verified measurements are never recovery candidates.

### Recovery rules

```text
0 matching unverified candidates
-> controller IDLE

1 matching unverified candidate
-> controller CANDIDATE_PENDING(current_measurement_id=...)

more than 1 matching unverified candidate
-> AmbiguousPendingMeasurementRecovery

explicit measurement_id
-> exact candidate only; fail if missing, verified or context-mismatched
```

There is intentionally no "newest wins" heuristic.

### Transient states

`AWAITING_VALUE`, `VERIFIED` and `REJECTED` are not independently persisted. After restart they recover as `IDLE` unless an actionable unverified candidate exists. Verified measurement facts remain durable in the session itself.

## Truth/provenance boundary

No provenance or verification rule changed.

A recovered voice/OCR/device/manual candidate remains unverified. It becomes verified only through the existing explicit user-confirmation transition. Recovery itself does not create, edit, confirm or delete a measurement.

## Files changed

Added:

- `src/physical_measurement/recovery.py`;
- `tests/test_pass17_hands_free_recovery.py`;
- `docs/PASS_17_BUILD_REUSE_CHECK.md`;
- `docs/IMPLEMENTATION_REPORT_PASS_17.md`.

Modified:

- `src/physical_measurement/__init__.py`.

No shared contract, canonical fixture, adjacent slice implementation, repository-wide CI or persistence payload schema is modified.

## Test coverage

Pass-17 tests cover:

1. SQLite pending candidate survives reopen and can be explicitly confirmed;
2. no matching candidate returns `IDLE`;
3. multiple exact matches fail closed without session mutation;
4. explicit `measurement_id` safely disambiguates;
5. verified measurements cannot be resumed as pending;
6. explicit context mismatch fails closed;
7. `AWAITING_VALUE` is not invented after restart;
8. pending manual fallback can resume and confirm;
9. recovered candidate follows the existing correction flow with a new unverified candidate.

Repository CI remains authoritative for the complete Chat-2 and adjacent boundary suites.

## Shared-contract impact

None. No Change Request required.

## Remaining limits

- recovery requires the caller to reconstruct the intended measurement context (view/anchors/evidence/instrument/uncertainty);
- rejected-candidate history is not persisted because existing service semantics remove rejected candidates from the active session;
- multi-process concurrent mutation remains fail-closed through normal service/repository behavior but is not a dedicated stress-tested workflow in this pass;
- no provider-specific speech/OCR/device integration is added.
