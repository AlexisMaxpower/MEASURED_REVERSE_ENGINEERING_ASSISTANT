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
5. canonical fixtures в `tests/fixtures/contracts/`.

При конфликте локальной документации с canonical contract приоритет имеет `core/contracts/`.

## Структура

- `src/physical_measurement/` — внутренняя реализация Chat 2;
- `src/physical_measurement/boundary.py` — adapter internal Phase A → canonical shared contracts;
- `tests/test_phase_a.py` — unit tests Phase A;
- `tests/test_contract_boundary.py` — canonical contract/integration tests;
- `pyproject.toml` — локальная Python/test configuration Chat 2;
- `docs/CHAT_2_ROLE.md` — документация роли и границ ownership;
- `docs/PHASE_A_MANUAL_MEASUREMENT.md` — реализованный Phase A baseline;
- `docs/IMPLEMENTATION_REPORT_PHASE_A.md` — отчёт Phase A;
- `docs/IMPLEMENTATION_REPORT_CANONICAL_BOUNDARY.md` — отчёт integration gate Chat 6.

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

Candidate не может автоматически стать verified: confirmation выполнена отдельным явным state transition.

### Canonical boundary — implemented

Выполнена директива Chat 6 `OD-2026-09-29-001`:

```text
canonical CapturePackage
→ Phase A MeasurementSession
→ manual verified PhysicalMeasurement
→ CanonicalMeasurementAdapter
→ canonical MeasurementPackage
→ JSON Schema validation
```

Текущие внутренние manual anchors хранятся в пикселях, поэтому на shared boundary честно сериализуются как `IMAGE_PX`. Преобразование в `MAT_XY_MM` не выполняется без отдельного calibration-aware шага.

Adapter проверяет:

- `CapturePackage.schema_version`;
- совпадение `project_id`;
- существование `view_id`;
- соответствие `reference_frame_id` canonical clean reference frame;
- существование `evidence_frame_id` в measurement frames, если evidence указан;
- сохранение provenance и explicit confirmation;
- формирование canonical `MeasurementPackage`.

Локальная проверка этой итерации:

```text
9 passed
```

Contract test использует repository-owned:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `tests/fixtures/contracts/capture_package_v1.json`.

## Следующий рабочий порядок

1. Перед новой итерацией перечитать `ORCHESTRATOR_DIRECTIVE.md`.
2. Передать результат Chat 6 на integration acceptance.
3. После принятия canonical boundary перейти к следующему gate, назначенному Orchestrator.
4. Phase B snapping не начинать, если Chat 6 выдаст более приоритетную интеграционную задачу.
5. Shared contracts не редактировать напрямую.
