# Chat 1 — Project & Guided Capture

Эта директория является изолированной рабочей областью Chat 1 проекта MREA.

## Ownership

Chat 1 отвечает за вертикальный слайс `Project & Guided Capture`: создание проекта, CapturePlan, camera workflow, guided capture, Measurement Mat detection, calibration, clean reference frame, measurement-frame capture, voice capture trigger, image-quality analysis и формирование `CapturePackage`.

Chat 1 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Структура

- `MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md` — копия исходного SSOT, переданного пользователем.
- `docs/` — рабочая документация Chat 1.

## Текущее состояние

Репозиторий был пустым на момент создания этой области. Код вертикального слайса ещё не реализован. До начала реализации необходимо получить утверждённые Integrator-ом v1 schemas/fixtures для `ProjectContract`, `CapturePackage`, `MeasurementCaptureFrame` и `ArtifactReference` либо зафиксировать соответствующий Change Request.
