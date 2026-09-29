# Chat 2 — Physical Measurement

Эта директория является изолированной рабочей областью Chat 2 проекта MREA.

## Ownership

Chat 2 отвечает за вертикальный слайс `Physical Measurement`: MeasurementSession, measurement types, annotation UX, feature anchor selection, snapping, OCR pipeline, voice value, user confirmation, caliper detection research, jaw/contact estimation, evidence, provenance и формирование `MeasurementPackage`.

Chat 2 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Структура

- `src/physical_measurement/` — внутренняя реализация Chat 2.
- `tests/` — локальные unit tests вертикального слайса.
- `pyproject.toml` — локальная Python/test configuration Chat 2.
- `docs/CHAT_2_ROLE.md` — документация роли и границ ownership.
- `docs/PHASE_A_MANUAL_MEASUREMENT.md` — реализованный Phase A baseline.
- `docs/IMPLEMENTATION_REPORT_PHASE_A.md` — отчёт о реализации и проверке Phase A.

## Текущее состояние

### Phase A — implemented

Реализован внутренний baseline:

```text
MeasurementSession
→ manual anchor A/B
→ measurement type
→ manual numeric value
→ MANUAL_MEASURED candidate
→ explicit user confirmation
→ USER_CONFIRMED verified measurement
```

Поддержаны все measurement types, перечисленные в SSOT. Значения измерений хранятся через `Decimal`. Candidate не может автоматически стать verified: confirmation выполнена отдельным явным state transition.

Добавлен in-memory repository boundary для unit-тестов и отделения application logic от будущего persistence implementation.

Локальная проверка перед загрузкой:

```text
6 passed in 0.06s
```

### Shared integration — blocked by Integrator contracts

Canonical shared contracts/fixtures v1 в repository пока не обнаружены. Поэтому Chat 2 намеренно не создавал собственные shared schemas для:

- `CapturePackage`;
- `MeasurementCaptureFrame`;
- `PhysicalMeasurement`;
- `MeasurementPackage`;
- `ArtifactReference`.

Внутренний `FeatureAnchor` также не объявляется canonical cross-slice representation.

## Ближайший рабочий порядок

1. Получить canonical contracts/fixtures v1 от Integrator.
2. Добавить `CapturePackage -> MeasurementSession` adapter.
3. Добавить mapper internal measurement -> canonical `PhysicalMeasurement`.
4. Реализовать canonical `MeasurementPackageBuilder`.
5. Добавить contract/integration tests.
6. Добавить offline-safe persistence.
7. После стабильной Phase A integration перейти к Phase B — snapping.
8. Далее: OCR → voice value → caliper/jaw/contact CV.
