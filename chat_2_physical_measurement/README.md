# Chat 2 — Physical Measurement

Эта директория является изолированной рабочей областью Chat 2 проекта MREA.

## Ownership

Chat 2 отвечает за вертикальный слайс `Physical Measurement`: MeasurementSession, measurement types, annotation UX, feature anchor selection, snapping, OCR pipeline, voice value, user confirmation, caliper detection research, jaw/contact estimation, evidence, provenance и формирование `MeasurementPackage`.

Chat 2 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Координация

Перед каждой следующей итерацией Chat 2 читает:

1. актуальный `main`;
2. `ORCHESTRATOR_DIRECTIVE.md`;
3. `core/contracts/mrea_contracts_v1.schema.json`;
4. `core/contracts/POLICIES_V1.md`;
5. canonical fixtures в `tests/fixtures/contracts/`;
6. актуальный Chat 6 pass plan / workflow.

При конфликте локальной документации с canonical contract или активной директивой Chat 6 приоритет имеет canonical/Chat 6 source of truth.

## Структура

- `src/physical_measurement/models.py` — internal measurement domain;
- `src/physical_measurement/service.py` — MeasurementSession application service;
- `src/physical_measurement/hands_free.py` — provider-independent command parser + hands-free state machine;
- `src/physical_measurement/boundary.py` — internal measurement → canonical shared-contract adapter;
- `tests/test_phase_a.py` — manual baseline tests;
- `tests/test_contract_boundary.py` — canonical boundary tests;
- `tests/test_pass2_raw_output.py` — deterministic real raw IMAGE_PX output tests;
- `tests/test_pass3_hands_free.py` — hands-free parser/state-transition tests;
- `docs/BUILD_REUSE_CHECK_PASS_3.md` — Pass 3 dependency decision;
- `docs/IMPLEMENTATION_REPORT_PASS_3.md` — Pass 3 implementation report;
- `ORCHESTRATOR_HANDOFF.md` — final source-of-truth handoff for Chat 6 review.

## Текущее состояние

### Phase A manual baseline — accepted

```text
MeasurementSession
→ manual anchor A/B
→ measurement type
→ manual numeric value
→ MANUAL_MEASURED candidate
→ explicit user confirmation
→ USER_CONFIRMED verified measurement
```

Manual candidate не становится verified автоматически.

### Canonical raw measurement boundary — accepted

Chat 2 сохраняет реальные image-space anchors как `IMAGE_PX`. `IMAGE_PX → MAT_XY_MM` normalization принадлежит Chat 3 и использует CapturePackage calibration.

Canonical adapter сохраняет:

- measurement type/value/unit;
- provenance;
- `view_id`;
- reference frame через anchors;
- evidence frame;
- uncertainty/instrument;
- explicit `verified` + `confirmation_source`.

### Pass 3 hands-free domain baseline — implementation

Активная директива: `OD-2026-09-29-003`.

Добавлен provider-independent workflow:

```text
speech-provider text / OCR value / device value
→ deterministic parser or direct candidate API
→ unverified candidate
→ explicit confirm / reject / correct
→ verified measurement only after USER_CONFIRMED
```

Поддерживаемый narrow command grammar включает:

- `замер`;
- `замер 42,18` / `замер 42.18`;
- confirm;
- reject;
- correct.

Неоднозначные числа и illegal state transitions fail-closed. Speech/OCR provider SDK в domain layer отсутствует.

Manual entry остаётся fallback и может заменить pending reported candidate, но также требует explicit confirmation.

## Truth / provenance invariants

1. Voice/OCR/device output — candidate, не verified fact.
2. Verification требует отдельного explicit user confirmation transition.
3. Rejected candidate удаляется из active MeasurementSession.
4. Correction создаёт новый measurement candidate ID и не наследует verified state.
5. `VISION_DETECTED`, `AI_INFERRED` и derived provenance не принимаются как direct physical-measurement candidates.
6. Evidence/reference/view linkage сохраняется.
7. Raw image anchors остаются `IMAGE_PX`.

## Следующий рабочий порядок

1. Работать только по активной Chat 6 directive и своей pass branch.
2. Не менять shared contracts/CI без approved Change Request.
3. Перед handoff выполнить локальные tests и получить доступный GitHub CI evidence.
4. `ORCHESTRATOR_HANDOFF.md` — последний commit прохода; после handoff branch freeze до `FIX_REQUIRED`.
