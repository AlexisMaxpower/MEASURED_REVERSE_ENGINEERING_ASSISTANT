# Chat 4 — CAD Bridge & Verification

Эта директория является изолированной рабочей областью Chat 4 проекта MREA.

## Ownership

Chat 4 отвечает за вертикальный слайс `CAD Bridge & Verification`:

- canonical `SketchPackage` intake;
- SVG/DXF export;
- `CADPackage`;
- vendor-neutral CAD adapter/read-back boundary;
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
- `../tests/fixtures/contracts/`;
- `ORCHESTRATOR_DIRECTIVE.md`.

Slice-local models являются implementation details.

## Реализованный baseline

```text
SketchPackage v1
    ↓ canonical mapper
MappedSketchPackage
    ├─ internal CadSketch
    └─ verified dimensions
          ↓
      CadAdapter
          ↓
CadDimensionBinding + normalized CadReadBack
          ↓
      VerificationEngine
          ↓
internal VerificationReport
          ↓ canonical mapper
CADPackage v1 + CADVerificationReport v1
```

Generic layer:

- deterministic SVG exporter;
- DXF R12 exporter via `ezdxf`;
- canonical `CADPackage v1` builder;
- canonical `CADVerificationReport v1` builder;
- vendor-neutral `CadAdapter` protocol;
- explicit `dimension_id ↔ measurement_id ↔ vendor_dimension_ref` mapping;
- normalized CAD read-back in `mm` / `deg`;
- deterministic `TestDoubleCadAdapter`;
- full canonical golden flow without installed SOLIDWORKS;
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

Repository test inventory after the adapter-baseline change: **20 tests**.

Последний clean baseline до этой итерации: **14 tests, OK**. Новый adapter/pipeline набор отдельно выполнен: **6 tests, OK**. Fresh full 20-test checkout run остаётся integration verification item, потому что текущий execution container не имеет outbound DNS к GitHub.

Contract tests читают реальные canonical schema/fixtures из repository root, а не локальные копии.

## Текущий следующий этап

Generic CAD gate закрыт. Следующий vendor-specific этап — SOLIDWORKS C#/.NET/COM adapter за уже существующим normalized boundary.

До реализации необходимо зафиксировать target environment:

- supported SOLIDWORKS version;
- .NET target;
- interop strategy;
- Windows/SOLIDWORKS test host.

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
