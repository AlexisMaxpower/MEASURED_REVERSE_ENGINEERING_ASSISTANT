# Chat 4 — CAD Bridge & Verification

**Проект:** MREA — Measured Reverse Engineering Assistant  
**Роль:** Chat 4  
**Vertical slice:** CAD Bridge & Verification  
**Источник истины:** MREA SSOT v0.1 от 2026-09-29  
**Статус документа:** актуализирован при подключении Chat 4 к репозиторию  
**Дата:** 2026-09-29

---

## 1. Назначение роли

Chat 4 отвечает за переход от структурированного `SketchPackage` к CAD-артефактам и за доказуемую проверку того, что verified physical measurements корректно перенесены в CAD.

Основная задача — не просто экспортировать геометрию, а сохранить traceability:

```text
PhysicalMeasurement
→ SketchPackage dimension
→ CAD dimension
→ CAD read-back
→ Verification result
```

Результат должен позволять определить для каждого verified measurement, совпадает ли фактическое значение в CAD с ожидаемым, отсутствует ли размер или возник ли constraint conflict.

---

## 2. Ownership

Chat 4 отвечает за:

- SVG export;
- DXF export;
- CAD adapter interface;
- SOLIDWORKS adapter;
- creation of sketch;
- creation of CAD geometry entities;
- CAD dimensions;
- CAD constraints;
- сохранение `measurement_id` mapping;
- CAD read-back;
- verification engine;
- `CADVerificationReport` generation;
- CAD integration tests.

### Основные логические компоненты

На уровне архитектурной ответственности Chat 4 понадобятся:

- generic CAD export layer;
- CAD adapter abstraction;
- SVG adapter/exporter;
- DXF adapter/exporter;
- SOLIDWORKS adapter;
- CAD entity/dimension mapping;
- read-back abstraction;
- verification engine;
- verification report builder;
- CAD integration-test harness.

Точные имена файлов, классов и директорий должны определяться только после появления актуальной repository architecture и не фиксируются этим документом заранее.

---

## 3. Что не входит в ownership Chat 4

Chat 4 не отвечает за:

- camera workflow;
- CapturePackage generation;
- measurement extraction;
- OCR/voice measurement semantics;
- определение значения `PhysicalMeasurement`;
- geometry semantics;
- contour/primitive detection;
- построение `GeometryGraph`;
- lifecycle;
- revision/manufacturing/install/test/failure flow.

Chat 4 не изменяет самостоятельно:

- shared contracts;
- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- глобальную архитектуру;
- ownership соседних слайсов.

Эти области принадлежат Integrator.

---

## 4. Upstream inputs

Главный upstream contract:

`SketchPackage`

SSOT определяет его как основной контракт между Geometry и CAD.

Ожидаемые категории данных:

- package version;
- project/part identity;
- view;
- coordinate system;
- entities;
- constraints;
- dimensions;
- unresolved items;
- source views.

Для dimension критически важны:

- `dimension_id`;
- `measurement_id`;
- expected numeric value;
- unit;
- provenance/source;
- verified flag.

Canonical schema принадлежит Integrator. Chat 4 не должен самостоятельно расширять или менять shared contract для удобства adapter implementation.

---

## 5. Downstream outputs

Chat 4 производит:

- SVG artifact;
- DXF artifact;
- CAD-native artifact через adapter;
- read-back representation/result;
- `CADVerificationReport`.

Canonical `CADPackage` и `CADVerificationReport` являются shared contracts и должны утверждаться Integrator.

---

## 6. Verification statuses

Обязательные статусы:

- `VERIFIED`;
- `MISMATCH`;
- `MISSING`;
- `CONSTRAINT_CONFLICT`.

Смысл:

### VERIFIED

CAD read-back найден и совпадает с verified expected value в утверждённом tolerance.

### MISMATCH

CAD dimension существует, но read-back value не соответствует expected value.

### MISSING

Ожидаемая verified dimension не найдена в CAD/read-back mapping.

### CONSTRAINT_CONFLICT

CAD/constraint solver не способен удовлетворить required verified dimensions/constraints без конфликта.

Никакой из этих статусов не может быть молча преобразован в успешный результат.

---

## 7. Главный метрологический инвариант

Verified physical measurement имеет приоритет над image-derived или inferred geometry.

Если expected value и CAD actual value расходятся, Chat 4 обязан зафиксировать расхождение, а не менять expected measurement.

Пример:

```text
expected = 5.18 mm
actual   = 5.31 mm
status   = MISMATCH
```

Запрещено:

- silently correct expected value;
- silently correct CAD result и скрыть факт изменения;
- потерять `measurement_id` mapping;
- считать inferred geometry эквивалентом verified physical measurement.

---

## 8. CAD Bridge levels

### Level 1 — Generic interchange

Первая ступень:

- SVG;
- DXF;
- JSON `SketchPackage` input.

Цель — deterministic export без зависимости от конкретной CAD-системы.

### Level 2 — Native adapters

После generic bridge:

- SOLIDWORKS;
- AutoCAD;
- FreeCAD;
- Fusion/other adapters при необходимости.

Первый обязательный native adapter по SSOT — SOLIDWORKS.

---

## 9. SOLIDWORKS baseline

Технологический baseline:

```text
C#
.NET
SOLIDWORKS API
COM
```

SOLIDWORKS adapter должен уметь:

1. принять `SketchPackage`;
2. создать sketch;
3. создать supported geometry entities;
4. создать supported dimensions;
5. создать supported constraints;
6. сохранить связь с `measurement_id`;
7. прочитать итоговый sketch обратно;
8. сформировать данные для `CADVerificationReport`.

---

## 10. Adapter architecture principle

Verification logic не должна быть зашита исключительно внутрь SOLIDWORKS-specific COM-кода.

Архитектурная цель:

```text
SketchPackage
→ normalized adapter input
→ CAD adapter
→ CAD artifact
→ normalized read-back
→ generic verification engine
→ CADVerificationReport
```

Это позволяет:

- тестировать verification без установленного SOLIDWORKS;
- повторно использовать правила проверки для DXF/FreeCAD/других adapters;
- отделить CAD API failures от метрологической verification logic;
- создавать fixture-driven tests.

---

## 11. Determinism

Одинаковый валидный `SketchPackage` при одинаковой версии adapter/exporter должен приводить к воспроизводимому логическому результату.

Для текстовых interchange formats, где возможно, output должен быть deterministic настолько, чтобы golden tests могли сравнивать canonical representation.

CAD-native файлы могут содержать vendor-generated metadata, поэтому golden verification должна опираться прежде всего на normalized read-back и semantic content, а не обязательно на byte-for-byte equality бинарного файла.

Это архитектурная рекомендация Chat 4; конкретный release gate утверждает Integrator.

---

## 12. Golden acceptance case

Минимальный acceptance fixture должен подтверждать:

```text
80.20 → 80.200 VERIFIED
42.10 → 42.100 VERIFIED
5.10  → 5.100 VERIFIED
60.00 → 60.000 VERIFIED
```

Golden end-to-end case SSOT использует простую плоскую деталь с:

- внешним контуром;
- двумя отверстиями;
- одним radius;
- одной thickness.

FRONT sketch должен пройти CAD import и read-back verification без скрытых mismatch.

---

## 13. Error handling

Chat 4 обязан различать как минимум:

- invalid/unsupported `SketchPackage` input;
- unsupported entity;
- unsupported constraint;
- unsupported dimension type;
- adapter/API failure;
- CAD application unavailable;
- entity creation failure;
- dimension creation failure;
- lost measurement mapping;
- read-back failure;
- `MISMATCH`;
- `MISSING`;
- `CONSTRAINT_CONFLICT`.

Ошибки integration layer не должны маскироваться как verification success.

---

## 14. Build / Reuse baseline

Перед нетривиальной реализацией должен выполняться Build / Reuse Check.

Не нужно писать с нуля:

- CAD kernel;
- DXF parser/writer, если стабильная библиотека покрывает требования;
- универсальный geometry solver;
- аналог SOLIDWORKS/AutoCAD.

Собственная ценность Chat 4 находится в:

- adapter orchestration;
- measurement mapping;
- normalized read-back;
- deterministic verification;
- traceability;
- error visibility.

Для выбора DXF/SVG/.NET libraries требуется отдельная проверка лицензии, зрелости, platform support и lock-in перед добавлением dependency.

---

## 15. Test strategy

### Unit tests

Для pure logic:

- mapping;
- normalization;
- tolerance comparison;
- status classification;
- report building.

### Contract tests

После публикации canonical schemas:

- `SketchPackage` input validation;
- `CADVerificationReport` output validation;
- fixture compatibility.

### Golden tests

- known SketchPackage → expected normalized SVG/DXF semantics;
- expected verified dimensions → exact verification statuses.

### SOLIDWORKS integration tests

Должны проверять:

- COM/API connection;
- sketch creation;
- entities;
- dimensions;
- constraints;
- `measurement_id` mapping;
- read-back;
- mismatch visibility.

Окружение SOLIDWORKS integration tests должно быть явно отделено от обычных unit tests, потому что требует Windows + установленный SOLIDWORKS/API runtime.

---

## 16. MVP / Roadmap relation

Глобальный roadmap:

- R3 — SketchPackage + DXF/SVG;
- R5 — SOLIDWORKS Integration: C# adapter, sketch creation, dimensions, verification.

Для Chat 4 практическая последовательность:

### Phase A — Contract reconnaissance

- получить canonical `SketchPackage` schema/fixture;
- получить canonical `CADVerificationReport` schema/fixture;
- проверить supported v1 entities/constraints/dimensions.

### Phase B — Verification core

- normalized expected dimensions;
- normalized read-back model;
- tolerance policy integration;
- statuses;
- report builder.

### Phase C — Generic export

- SVG;
- DXF;
- deterministic/golden tests.

### Phase D — CAD adapter abstraction

- adapter interface;
- capability reporting;
- normalized errors;
- normalized read-back.

### Phase E — SOLIDWORKS adapter

- C#/.NET project;
- COM/API integration;
- entity creation;
- dimensions/constraints;
- mapping;
- read-back.

### Phase F — Integration verification

- golden fixture;
- mismatch fixture;
- missing fixture;
- constraint-conflict fixture;
- integration report.

---

## 17. Acceptance Criteria

Chat 4 slice считается выполненным, когда:

- валидный upstream `SketchPackage` читается;
- SVG/DXF создаются для поддерживаемого v1 subset;
- SOLIDWORKS adapter создаёт sketch для golden fixture;
- supported entities/dimensions/constraints переносятся;
- verified dimensions сохраняют связь с `measurement_id`;
- read-back получает фактические CAD values;
- формируется canonical `CADVerificationReport`;
- `VERIFIED`, `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT` различаются;
- mismatch никогда не скрывается;
- contract tests проходят;
- CAD integration tests проходят в supported SOLIDWORKS environment;
- документация актуализирована.

---

## 18. Текущие зависимости от Integrator

На момент подключения Chat 4 repository не содержит canonical shared schemas/fixtures.

Необходимы:

- `SketchPackage` v1 schema;
- `sketch_package_v1.json` fixture;
- `CADPackage` v1 schema, если он используется как отдельный contract;
- `CADVerificationReport` v1 schema;
- `cad_verification_v1.json` fixture;
- canonical tolerance/units policy, если она не является частью contract;
- supported v1 subset entities/constraints/dimension types, если schema допускает более широкий набор.

Если этих данных недостаточно для реализации, Chat 4 должен оформить Change Request, а не изменять shared contract самостоятельно.

---

## 19. Change Request template

```text
CHANGE_REQUEST

Requester: Chat 4 — CAD Bridge & Verification
Contract:
Problem:
Current behavior:
Requested change:
Reason:
Affected chats:
Backward compatible: YES/NO
Migration:
```

---

## 20. Definition of Done для Chat 4

Помимо локальных acceptance criteria применяются общие правила SSOT:

- пользовательский сценарий работает;
- upstream contract читается;
- downstream contract создаётся;
- contract tests проходят;
- fixtures валидны;
- ошибки не скрываются;
- документация обновлена;
- чужие ownership-модули не затронуты;
- отсутствуют незадокументированные временные workaround.
