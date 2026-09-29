# Chat 4 — CAD Bridge & Verification

Эта директория является изолированной рабочей областью Chat 4 проекта MREA.

## Ownership

Chat 4 отвечает за вертикальный слайс `CAD Bridge & Verification`:

- экспорт `SketchPackage` в SVG/DXF;
- общий CAD adapter interface;
- SOLIDWORKS adapter;
- создание CAD sketch;
- создание geometry entities;
- создание CAD dimensions и constraints;
- сохранение связи CAD dimensions с `measurement_id`;
- read-back созданного sketch;
- сравнение ожидаемых verified measurements с фактическими CAD values;
- формирование `CADVerificationReport`;
- CAD integration tests.

Chat 4 не владеет capture, measurement extraction, geometry semantics, lifecycle или shared contracts и не изменяет их без решения Integrator.

## Технологический baseline

SOLIDWORKS integration:

- C#;
- .NET;
- SOLIDWORKS API;
- COM.

Generic CAD bridge должен начинаться с форматов:

- SVG;
- DXF;
- JSON `SketchPackage` как входного контракта.

## Структура

- `README.md` — границы рабочей области Chat 4.
- `docs/CHAT_4_ROLE.md` — подробная документация роли, контрактов, архитектурных правил и acceptance criteria.
- `docs/IMPLEMENTATION_STATE.md` — текущее состояние реализации, зависимости, блокеры и последовательность разработки.

## Текущее состояние

На момент подключения Chat 4 в репозитории существует область Chat 1, но отсутствуют canonical shared-contract schemas/fixtures и runtime-код CAD bridge.

Код Chat 4 пока не реализован. До интеграционной реализации необходимо получить утверждённый Integrator-ом `SketchPackage` fixture/schema и canonical `CADVerificationReport` contract. Локальные adapter abstractions и export/verification design могут разрабатываться без изменения shared contracts.

## Главный инвариант

Ни один mismatch между verified physical measurement и CAD read-back не должен скрываться или автоматически исправляться.

Допустимые verification statuses:

- `VERIFIED`;
- `MISMATCH`;
- `MISSING`;
- `CONSTRAINT_CONFLICT`.
