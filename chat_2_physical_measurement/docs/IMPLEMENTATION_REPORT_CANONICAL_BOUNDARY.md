# IMPLEMENTATION_REPORT — Chat 2 Canonical Boundary

**Дата:** 2026-09-29  
**Chat:** 2 — Physical Measurement  
**Directive:** `OD-2026-09-29-001`

## 1. Что реализовано

Добавлен shared-boundary adapter между внутренними Phase A dataclasses Chat 2 и canonical shared contracts Integrator.

Реализован поток:

```text
CapturePackage fixture
→ MeasurementSession
→ manual anchors
→ manual numeric candidate
→ explicit user confirmation
→ CanonicalMeasurementAdapter
→ MeasurementPackage
→ JSON Schema validation
```

## 2. Исходные contracts

Использованы без изменения:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/capture_package_v1.json`;
- `tests/fixtures/contracts/measurement_package_v1.json` как reference example.

Canonical shared contracts не редактировались.

## 3. Изменённые/добавленные файлы

- `src/physical_measurement/boundary.py`;
- `src/physical_measurement/__init__.py`;
- `tests/test_contract_boundary.py`;
- `pyproject.toml`;
- `README.md`;
- `docs/IMPLEMENTATION_REPORT_CANONICAL_BOUNDARY.md`.

## 4. Зависимости

В test extra добавлен:

```text
jsonschema>=4.23,<5
```

Он используется только для проверки repository-owned JSON Schema в contract tests.

## 5. Тесты

Добавлены проверки:

- canonical CapturePackage fixture проходит `CapturePackage` schema;
- manual verified measurement сериализуется в schema-valid `MeasurementPackage`;
- provenance `MANUAL_MEASURED` сохраняется;
- confirmation `USER_CONFIRMED` сохраняется;
- current pixel anchors сериализуются как `IMAGE_PX`;
- IDs `project_id`, `part_id`, `capture_package_id` наследуются из upstream package;
- session с другим project rejected;
- anchor с reference frame, отсутствующим в upstream CapturePackage, rejected.

## 6. Результат проверки

```text
9 passed
```

Проверка выполнена локально на актуальной Phase A реализации с canonical schema subset, соответствующим опубликованным `FeatureAnchor`, `PhysicalMeasurement`, `MeasurementPackage` и `CapturePackage`; repository test при запуске читает полную schema непосредственно из `core/contracts/mrea_contracts_v1.schema.json`.

## 7. Что не проверено

- CI repository-wide;
- persistence после рестарта процесса;
- mobile annotation UX;
- перевод manual anchor из `IMAGE_PX` в `MAT_XY_MM`;
- OCR / voice / snapping / caliper CV.

## 8. Известные ограничения

- internal Phase A `FeatureAnchor` пока хранит только pixel coordinates;
- `feature_id` на canonical boundary сейчас `null`;
- confidence для manual Phase A сериализуется как `null`;
- Phase A internal model всё ещё использует поле `uncertainty_mm`, поэтому angle-specific uncertainty требует отдельной нормализации до расширения ANGLE workflow;
- evidence reference допускается только если соответствующий frame реально присутствует в upstream CapturePackage.

## 9. Новые технические знания

Canonical boundary позволяет независимо развивать внутреннюю модель Chat 2 и shared wire contract. Это сохраняет ownership Integrator и снижает связанность между слайсами.

`IMAGE_PX` используется для текущих manual anchors, потому что преобразование в `MAT_XY_MM` без calibration-aware операции создало бы ложную метрическую семантику.

## 10. Change Requests

Нет.

Текущая canonical schema достаточна для integration gate `OD-2026-09-29-001`.

## 11. Что готово к интеграции

Готово к проверке Chat 6:

```text
canonical CapturePackage
→ Chat 2 manual verified measurement
→ canonical schema-valid MeasurementPackage
```
