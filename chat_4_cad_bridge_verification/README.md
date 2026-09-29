# Chat 4 — CAD Bridge & Verification

Эта директория является изолированной рабочей областью Chat 4 проекта MREA.

## Ownership

Chat 4 отвечает за вертикальный слайс `CAD Bridge & Verification`:

- canonical `SketchPackage` intake;
- SVG/DXF export;
- `CADPackage`;
- общий CAD adapter interface;
- SOLIDWORKS adapter;
- создание CAD sketch/entities/dimensions/constraints;
- сохранение связи CAD dimensions с `dimension_id` и `measurement_id`;
- CAD read-back;
- `CADVerificationReport`;
- CAD integration tests.

Chat 4 не владеет capture, measurement extraction, geometry semantics, lifecycle или shared contracts.

## Source of truth

Для cross-slice boundary используются только:

- `../core/contracts/mrea_contracts_v1.schema.json`;
- `../core/contracts/POLICIES_V1.md`;
- `../tests/fixtures/contracts/`.

Slice-local models являются implementation details.

## Реализованный baseline

```text
SketchPackage v1
    ↓ canonical mapper
MappedSketchPackage
    ├─ internal CadSketch
    ├─ canonical entities/dimensions/constraints/unresolved
    └─ verified dimensions + transfer tolerance
          ↓
      VerificationEngine
          ↓
internal VerificationReport
          ↓ canonical mapper
CADVerificationReport v1
```

Также реализованы:

- deterministic SVG exporter;
- DXF R12 exporter через `ezdxf`;
- `CADPackage v1` builder;
- canonical golden contract tests;
- no-silent-correction verification statuses.

## Dependencies

Runtime:

```text
ezdxf==1.4.4
```

Development / contract tests:

```text
jsonschema==4.26.0
```

## Проверка

Из `chat_4_cad_bridge_verification/`:

```text
pip install -r requirements-dev.txt
PYTHONPATH=src python -m unittest discover -s tests -v
```

Текущий baseline: **14 tests, OK**.

Contract tests читают реальные canonical schema/fixtures из repository root, а не локальные копии.

## Текущий следующий этап

Canonical contract blocker снят. Следующий vendor-specific этап — SOLIDWORKS C#/.NET/COM adapter и CAD read-back. Он остаётся зависимым от утверждённого Windows/SOLIDWORKS target environment.

## Главный инвариант

Verified physical value не корректируется по CAD read-back.

Допустимые item statuses:

- `VERIFIED`;
- `MISMATCH`;
- `MISSING`;
- `CONSTRAINT_CONFLICT`.

Canonical `overall_status`:

- `VERIFIED`;
- `FAILED`.
