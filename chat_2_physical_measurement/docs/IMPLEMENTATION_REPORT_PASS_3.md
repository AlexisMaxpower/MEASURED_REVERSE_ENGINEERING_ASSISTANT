# Chat 2 — Pass 3 Hands-Free Measurement Domain Baseline

**Directive:** `OD-2026-09-29-003`  
**Branch:** `chat-2/pass-3`  
**Date:** 2026-09-29

## 1. Реализовано

Добавлен provider-independent hands-free measurement baseline без speech/OCR SDK dependency.

Поток voice command:

```text
text from any speech provider
→ MeasurementCommandParser
→ deterministic intent/value
→ HandsFreeMeasurementController
→ unverified PhysicalMeasurement candidate
→ explicit confirm / reject / correct
→ USER_CONFIRMED verified measurement only after confirm
```

Прямой provider-neutral поток OCR/device:

```text
OCR/device adapter value
→ submit_candidate(value, truthful provenance)
→ unverified candidate
→ explicit confirmation
→ verified measurement
```

## 2. Команды Pass 3

Поддерживается минимальная deterministic grammar:

- `замер` → trigger / ожидание значения;
- `замер 42,18` → voice candidate `42.18`;
- `замер 42.18` → тот же normalized value;
- optional `мм` / `mm` после одного numeric token;
- `подтвердить`, `подтверди`, `подтверждаю` → explicit confirmation;
- `отклонить`, `отклони`, `отмена`, `отменить` → reject;
- `исправить <value>`, `исправь <value>`, `коррекция <value>` → discard old candidate + create corrected unverified voice candidate.

Не выполняется guessing словесных чисел или нескольких numeric tokens. Неоднозначный ввод отклоняется.

## 3. State machine

Phases:

- `IDLE`;
- `AWAITING_VALUE`;
- `CANDIDATE_PENDING`;
- `VERIFIED`;
- `REJECTED`.

Illegal transitions raise `InvalidMeasurementTransition` вместо скрытого state mutation.

## 4. Provenance / truth policy

Candidate sources, разрешённые внутренней PhysicalMeasurement model:

- `MANUAL_MEASURED`;
- `VOICE_REPORTED`;
- `OCR_MEASURED`;
- `DEVICE_REPORTED`.

`VISION_DETECTED`, `AI_INFERRED`, derived/calibration provenance не могут войти в этот physical-measurement candidate path.

Voice/OCR/device/manual candidate имеет `verified = false` до отдельного explicit confirmation. Confirmation source остаётся `USER_CONFIRMED`.

Reject удаляет unverified candidate из active MeasurementSession, чтобы rejected value не попал в MeasurementPackage как активный measurement.

Correction отклоняет предыдущий candidate и создаёт новый candidate с новым measurement ID; corrected voice value остаётся `VOICE_REPORTED` и unverified.

## 5. Manual fallback

Существующий manual Phase A API сохранён без breaking change.

Дополнительно state machine умеет заменить pending reported candidate на `MANUAL_MEASURED` candidate. Manual fallback также требует explicit confirmation перед verified state.

## 6. Evidence / coordinate semantics

Новые candidates используют существующие FeatureAnchor/context поля и сохраняют:

- `view_id`;
- `reference_frame_id` через anchors;
- `evidence_frame_id`;
- `instrument_type`;
- uncertainty;
- provenance.

Canonical adapter не изменён: anchors по-прежнему выходят как raw `IMAGE_PX`, `feature_id = null`. Геометрическая normalization остаётся Chat 3 responsibility.

## 7. Backward compatibility

Сохранены существующие public methods:

- `add_manual_candidate`;
- `confirm_manual_measurement`.

Они делегируют расширенному provider-neutral candidate/confirmation path.

Добавлены:

- `add_candidate`;
- `add_reported_candidate`;
- `confirm_measurement`;
- `reject_candidate`.

## 8. Deterministic tests

Добавлен `tests/test_pass3_hands_free.py` с покрытием:

- trigger;
- comma/dot number normalization;
- optional mm unit;
- ambiguous multiple/mixed numeric input;
- invalid command;
- voice candidate stays unverified;
- OCR candidate stays unverified;
- device candidate stays unverified;
- explicit confirmation;
- reject;
- correct;
- manual fallback;
- invalid transitions;
- rejection of non-measurement provenance;
- canonical wire preservation for verified voice measurement.

Локально до публикации implementation branch:

```text
pytest -q tests/test_phase_a.py tests/test_pass3_hands_free.py
18 passed
```

Full repository-owned Chat 2/contract/integration gates будут проверяться canonical GitHub Actions после публикации branch.

## 9. Намеренно не реализовано

- speech recognition engine;
- OCR engine;
- device/caliper hardware protocol;
- automatic feature detection;
- geometry normalization;
- persistent recovery of hands-free controller state after process restart;
- natural-language number words (`сорок два`) or broad NLU grammar.

## 10. Shared contracts

Shared contracts/fixtures/CI не изменялись. Change Request не требуется.
