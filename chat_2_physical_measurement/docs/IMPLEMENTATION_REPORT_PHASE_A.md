# IMPLEMENTATION_REPORT — Chat 2 Phase A

**Дата:** 2026-09-29  
**Slice:** Physical Measurement  
**Phase:** A — Manual anchors + manual value  

## 1. Что реализовано

- internal `MeasurementSession` domain;
- полный SSOT registry measurement types;
- manual `FeatureAnchor`;
- manual measurement candidate;
- Decimal numeric normalization;
- provenance `MANUAL_MEASURED`;
- explicit user confirmation;
- confirmation provenance `USER_CONFIRMED`;
- view/reference-frame invariants для anchors;
- in-memory repository boundary;
- unit tests Phase A.

## 2. Какие исходные contracts использованы

Canonical shared contracts не использованы, потому что в repository пока отсутствуют утверждённые Integrator schemas/fixtures v1.

Использована только семантика SSOT:

- `MeasurementSession`;
- `PhysicalMeasurement` concept;
- measurement types;
- provenance categories;
- Phase A manual baseline;
- правило запрета silent verification.

Внутренние модели не объявляются canonical shared contracts.

## 3. Какие файлы изменены/добавлены

Добавлены:

- `src/physical_measurement/__init__.py`;
- `src/physical_measurement/models.py`;
- `src/physical_measurement/repository.py`;
- `src/physical_measurement/service.py`;
- `tests/test_phase_a.py`;
- `pyproject.toml`;
- `docs/PHASE_A_MANUAL_MEASUREMENT.md`;
- `docs/IMPLEMENTATION_REPORT_PHASE_A.md`.

README рабочей области обновляется отдельно текущим состоянием Phase A.

## 4. Какие зависимости добавлены

Runtime dependencies не добавлены.

Test-only:

- `pytest>=8,<9`.

## 5. Какие тесты добавлены

1. manual candidate не verified до confirmation;
2. explicit confirmation переводит measurement в verified;
3. silent confirmation запрещён;
4. measurement view обязан совпадать с anchor views;
5. anchors обязаны принадлежать одному reference frame;
6. registry measurement types совпадает с SSOT;
7. repository отдаёт изолированный snapshot session.

Фактически в `tests/test_phase_a.py` — 6 pytest test functions; первый тест проверяет сразу candidate и confirmation transition.

## 6. Какие тесты прошли

Локальный запуск на коде перед загрузкой в GitHub:

```text
6 passed in 0.06s
```

## 7. Что не проверено

- canonical contract compatibility;
- integration с Chat 1 `CapturePackage`;
- integration с Chat 3;
- database persistence;
- mobile UI;
- offline restart/recovery;
- real physical measurement workflow на устройстве.

## 8. Известные ограничения

- repository in-memory;
- anchor representation пока локальная Chat 2;
- Phase A поддерживает только manual source;
- `MeasurementPackage` не формируется до утверждения shared contract;
- API/UI отсутствуют;
- correction/rejection workflow пока не реализован отдельными transition methods.

## 9. Новые технические знания

- Для metric values выбран `Decimal`, чтобы не вносить binary floating-point artefacts в measured truth.
- Domain отделён от storage boundary, поэтому позже можно подключить SQLite/PostgreSQL/offline storage без переписывания measurement semantics.
- Confirmation оформлена отдельным state transition, что технически предотвращает silent promotion candidate -> verified.

## 10. Change Requests

Остаётся активным Change Request к Integrator на canonical v1 schemas/fixtures:

- `CapturePackage`;
- `MeasurementCaptureFrame`;
- `PhysicalMeasurement`;
- `MeasurementPackage`;
- `ArtifactReference`.

Дополнительно Integrator должен определить canonical anchor representation либо подтвердить, что anchors остаются внутренними до Geometry binding.

## 11. Что готово к интеграции

Готов internal Phase A domain baseline Chat 2.

Не готов shared integration boundary до появления canonical contracts/fixtures.
