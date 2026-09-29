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

## Реализованный baseline

Внутри Chat 4 уже есть независимый CAD-core:

- immutable internal 2D CAD model;
- deterministic SVG exporter;
- DXF R12 exporter через `ezdxf`;
- pure verification engine;
- unit tests;
- Build / Reuse Check;
- Change Request для отсутствующих canonical CAD contracts.

DXF serialization низкого уровня самостоятельно не реализуется. Используется:

```text
ezdxf==1.4.4
```

## Технологический baseline

SOLIDWORKS integration:

- C#;
- .NET;
- SOLIDWORKS API;
- COM.

Generic CAD bridge:

- SVG;
- DXF;
- JSON `SketchPackage` как будущий canonical input boundary.

## Структура

```text
chat_4_cad_bridge_verification/
├─ README.md
├─ requirements.txt
├─ src/
│  └─ mrea_cad_bridge/
│     ├─ model.py
│     ├─ adapter.py
│     ├─ verification.py
│     └─ exporters/
│        ├─ svg.py
│        └─ dxf.py
├─ tests/
│  ├─ test_exporters.py
│  └─ test_verification.py
└─ docs/
   ├─ CHAT_4_ROLE.md
   ├─ IMPLEMENTATION_STATE.md
   ├─ BUILD_REUSE_CHECK_CAD_CORE.md
   └─ CHANGE_REQUEST_001_CAD_CONTRACT_BASELINE.md
```

## Локальная проверка

```text
pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -s tests -v
```

Текущий baseline: 9 tests, `OK`.

DXF test не ограничивается проверкой строк: generated DXF повторно читается через `ezdxf.read()`.

## Текущий blocker

Canonical shared-contract schemas/fixtures для `SketchPackage` и `CADVerificationReport` пока не опубликованы Integrator-ом. Поэтому Chat 4 намеренно не создаёт собственные shared DTO и не реализует contract boundary по догадкам.

## Главный инвариант

Ни один mismatch между verified physical measurement и CAD read-back не должен скрываться или автоматически исправляться.

Допустимые verification statuses:

- `VERIFIED`;
- `MISMATCH`;
- `MISSING`;
- `CONSTRAINT_CONFLICT`.
