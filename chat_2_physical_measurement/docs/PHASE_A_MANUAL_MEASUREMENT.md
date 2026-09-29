# Chat 2 — Phase A Manual Measurement Baseline

**Статус:** implemented locally in Chat 2 ownership  
**Дата:** 2026-09-29  
**Scope:** manual anchors + manual value + explicit confirmation  

## 1. Цель

Phase A реализует первый полезный и низкорисковый baseline Physical Measurement без зависимости от OCR, voice, snapping или caliper CV.

Поток:

```text
project_id
→ MeasurementSession
→ manual anchor A
→ manual anchor B
→ measurement type
→ manual numeric value
→ MANUAL_MEASURED candidate
→ explicit user confirmation
→ USER_CONFIRMED verified measurement
```

Это внутренняя реализация Chat 2. Она намеренно не публикует собственную shared JSON schema для `PhysicalMeasurement` или `MeasurementPackage`, потому что shared contracts принадлежат Integrator.

## 2. Реализованные компоненты

### MeasurementType

Поддержан полный минимальный registry из SSOT:

- `LINEAR_EXTERNAL`
- `LINEAR_INTERNAL`
- `THICKNESS`
- `DEPTH`
- `DIAMETER_EXTERNAL`
- `DIAMETER_INTERNAL`
- `RADIUS`
- `ANGLE`
- `CENTER_DISTANCE`
- `SLOT_WIDTH`
- `SURFACE_DISTANCE`

### FeatureAnchor

Внутренний anchor хранит:

- `anchor_id`;
- `view_id`;
- `reference_frame_id`;
- pixel coordinates `x_px`, `y_px`.

Эта форма является локальной Chat 2 и не объявляется shared contract.

### PhysicalMeasurement

Внутренняя модель Phase A хранит:

- measurement identity;
- measurement type;
- Decimal numeric value;
- unit;
- provenance source;
- view;
- два anchors;
- optional evidence frame;
- optional uncertainty;
- optional instrument type;
- confirmation state;
- confirmation provenance;
- timestamps.

Phase A принимает только `MANUAL_MEASURED` как measurement source.

### MeasurementSession

Сессия хранит проект и набор measurements, обеспечивает уникальность measurement IDs и замену candidate на подтверждённую версию без мутации исходного объекта.

### MeasurementSessionService

Реализованы операции:

- create session;
- create manual anchor;
- add manual candidate;
- confirm manual measurement;
- read session.

### Repository boundary

Добавлен `InMemoryMeasurementSessionRepository` как локальная persistence boundary для unit-тестирования и отделения application logic от хранения.

Это не финальная persistence реализация и не repository-wide storage contract.

## 3. Инварианты

1. Measurement всегда имеет provenance.
2. Candidate не считается verified автоматически.
3. Phase A verification требует отдельного explicit user confirmation.
4. Confirmation фиксируется как `USER_CONFIRMED`.
5. Оба anchor должны принадлежать тому же view, что и measurement.
6. Оба anchor должны относиться к одному reference frame.
7. Anchor IDs внутри одного measurement должны различаться.
8. Numeric value хранится как `Decimal`, а не binary float.
9. Non-finite numeric values запрещены.
10. Negative anchor coordinates запрещены.
11. Shared contracts не создаются и не меняются.

## 4. Build / Reuse Check

```text
BUILD / REUSE CHECK

Проблема:
Нужен deterministic low-risk domain baseline для manual physical measurements.

Есть ли готовое open-source решение:
Общие validation/domain библиотеки существуют, но уникальная часть здесь — MREA measurement workflow,
provenance policy и confirmation semantics.

Можно ли использовать:
PARTIAL

Что используем:
Python standard library dataclasses, Decimal, Enum, UUID;
pytest только для тестов.

Что пишем сами:
Measurement session orchestration;
manual anchor semantics;
measurement provenance;
explicit confirmation transition;
local repository boundary.

Почему:
Это product/domain logic MREA и не является generic low-level задачей.

Lock-in risk:
LOW. Domain не привязан к web framework или database.

Fallback:
После утверждения Integrator contracts внутренние модели маппятся в canonical schemas.
```

## 5. Что намеренно не реализовано

- `CapturePackage` adapter;
- canonical `PhysicalMeasurement` JSON schema;
- canonical `MeasurementPackageBuilder`;
- contract tests;
- persistent database storage;
- REST API;
- mobile annotation UI;
- snapping;
- OCR;
- voice value;
- caliper/jaw/contact CV.

Причина первых четырёх пунктов — отсутствие утверждённых Integrator contracts/fixtures v1.

## 6. Следующий шаг

После появления canonical contracts:

1. добавить adapter `CapturePackage -> MeasurementSession input`;
2. добавить mapper internal measurement -> canonical `PhysicalMeasurement`;
3. реализовать `MeasurementPackageBuilder` по утверждённой schema;
4. добавить contract fixtures/tests;
5. заменить/дополнить in-memory persistence реальным offline-safe storage;
6. затем перейти к Phase B snapping.
