# Chat 2 — Physical Measurement

Эта директория является изолированной рабочей областью Chat 2 проекта MREA.

## Ownership

Chat 2 отвечает за вертикальный слайс `Physical Measurement`: MeasurementSession, measurement types, annotation UX, feature anchor selection, snapping, OCR pipeline, voice value, user confirmation, caliper detection research, jaw/contact estimation, evidence, provenance и формирование `MeasurementPackage`.

Chat 2 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Структура

- `README.md` — границы рабочей области Chat 2 и текущее состояние.
- `docs/CHAT_2_ROLE.md` — актуальная документация роли, входов/выходов, фаз реализации, acceptance criteria, рисков и Change Requests.

## Текущее состояние

На момент подключения Chat 2 репозиторий уже содержит рабочую область Chat 1, но canonical shared contracts/fixtures v1 в репозитории пока не обнаружены.

Поэтому первый безопасный этап разработки Chat 2 — подготовка `Phase A: Manual anchors + manual value` без изменения shared schemas. Для полноценной contract-driven реализации необходимы утверждённые Integrator-ом v1 schemas/fixtures как минимум для `CapturePackage`, `MeasurementCaptureFrame`, `PhysicalMeasurement`, `MeasurementPackage` и `ArtifactReference`.

## Ближайший рабочий порядок

1. Получить canonical contracts/fixtures v1 от Integrator.
2. Реализовать manual measurement baseline.
3. Зафиксировать provenance и evidence chain.
4. Добавить contract tests.
5. После стабильного baseline двигаться к snapping, затем OCR, voice и только потом caliper/jaw CV.
