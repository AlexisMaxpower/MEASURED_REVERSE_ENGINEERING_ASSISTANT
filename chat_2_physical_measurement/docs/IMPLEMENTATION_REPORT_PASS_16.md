# Chat 2 — Pass 16 Implementation Report

## Baseline

Pass 16 starts from accepted shared `main`:

`99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

Active directive: `OD-2026-10-01-008`.

At branch creation, Chat 2 Pass 15 existed as unmerged draft PR #49. Pass 16 therefore does not depend on Pass-15 persistence changes and does not modify `repository.py`, `service.py`, shared contracts, canonical fixtures or shared CI.

## Goal

Close the documented Phase-D gap between the Chat-2 voice workflow and its implementation: deterministic Russian spoken-number normalization for measurement value and correction commands while preserving candidate-only voice provenance and explicit user confirmation.

## Implementation

Extended `normalize_measurement_number(...)` with a finite, auditable Russian grammar.

Supported examples include:

```text
сорок два                          -> 42
сорок два восемнадцать             -> 42.18
сто один ноль пять                 -> 101.05
сорок два один восемь              -> 42.18
сорок две целых восемнадцать сотых -> 42.18
ноль целых пять сотых              -> 0.05
два целых пять тысячных            -> 2.005
```

Also supported:

- cardinal values through thousands;
- spoken `минус` / `плюс`;
- common `мм/mm/миллиметр...` and `градус...` suffixes;
- the existing numeric comma/dot forms unchanged;
- the same spoken grammar in `исправить ...` correction commands.

## Determinism / fail-closed policy

The parser deliberately does not guess under-specified forms.

Examples that fail closed:

- `сорок два пять` — fractional scale is ambiguous;
- mixed word/numeric payloads such as `сорок два 18`;
- incomplete explicit fractions;
- unsupported descriptive words such as `примерно`;
- conflicting sign representations.

Compact spoken decimals use an explicit two-decimal measurement convention only when the full token sequence is not already a valid whole-number cardinal. Thus `сорок два` is `42`, while `сорок два восемнадцать` is `42.18`.

## Truth boundary

No verification semantics changed.

```text
spoken provider text
-> deterministic Decimal candidate
-> VOICE_REPORTED
-> unverified PhysicalMeasurement
-> explicit confirmation
-> USER_CONFIRMED verified measurement
```

Invalid/ambiguous speech produces no measurement candidate.

## Files

Modified:

- `src/physical_measurement/hands_free.py`

Added:

- `tests/test_pass16_spoken_measurements.py`
- `docs/PASS_16_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_16.md`

Final handoff is recorded separately in `ORCHESTRATOR_HANDOFF.md` after executable CI evidence is available.

## Tests

`tests/test_pass16_spoken_measurements.py` covers:

1. whole spoken cardinals;
2. compact two-decimal caliper speech;
3. explicit tenths/hundredths/thousandths;
4. spoken signs and unit suffixes;
5. fail-closed mixed/under-specified forms;
6. compatibility with existing numeric input;
7. voice parser candidate creation;
8. explicit-confirmation preservation;
9. spoken correction semantics;
10. invalid descriptive speech producing no measurement truth.

Existing Pass-3 hands-free tests remain the regression surface for numeric commands and state transitions.

## Shared-contract impact

None.

No Change Request is required for this pass.

## Known limitations

- this is text normalization after speech recognition; no speech-recognition provider is added;
- grammar is intentionally finite rather than general Russian NLP;
- compact fractional speech is two-decimal only; other scales require explicit `десятых/сотых/тысячных` wording;
- millions and larger cardinals are not supported;
- controller restart-state durability remains separate future work.
