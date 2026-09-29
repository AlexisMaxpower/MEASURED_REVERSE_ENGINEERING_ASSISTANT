# Chat 3 — Geometry & Semi-Automatic Sketch

Эта директория является изолированной рабочей областью Chat 3 проекта MREA.

## Ownership

Chat 3 отвечает за вертикальный слайс `Geometry & Semi-Automatic Sketch`: модель `GeometryFeature`, contour extraction, обнаружение line/circle/arc primitives, `GeometryGraph`, candidates и разрешение constraints, binding verified measurements, geometry conflict detection, dimensioned view и формирование deterministic `SketchPackage`.

Главный инвариант слайса:

```text
verified physical measurement > image-derived estimate
```

Chat 3 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Вход / выход

```text
CapturePackage + MeasurementPackage
                ↓
        Geometry pipeline
                ↓
          SketchPackage
```

До появления canonical schemas/fixtures входы и выход не должны фиксироваться локальными несовместимыми контрактами.

## Структура

- `README.md` — границы рабочей области Chat 3.
- `docs/CHAT_3_ROLE.md` — актуальная документация роли, архитектурные инварианты и план реализации.
- `docs/IMPLEMENTATION_STATE.md` — фактическое состояние реализации и проверки.

## Текущее состояние

На момент подключения Chat 3 в `main` присутствует только область Chat 1; product code, shared contracts и canonical contract fixtures отсутствуют. Поэтому сейчас создана только изолированная область Chat 3 и документация. Реализация geometry pipeline начнётся после проверки опубликованных Integrator-ом v1 contracts/fixtures либо после формализации необходимых Change Requests.
