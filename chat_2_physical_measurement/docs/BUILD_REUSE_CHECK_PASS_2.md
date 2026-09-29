# BUILD / REUSE CHECK — Pass 2 Raw Measurement Specimen

**Chat:** 2 — Physical Measurement  
**Directive:** `OD-2026-09-29-002`  
**Pass:** 2

```text
BUILD / REUSE CHECK

Проблема:
Нужно получить воспроизводимый реальный wire output Chat 2 для межслайсовой проверки Chat 2 → Chat 3:
несколько verified measurements, raw IMAGE_PX anchors, evidence/provenance и deterministic test identities/timestamps.

Есть ли готовое open-source решение:
PARTIAL. JSON Schema validation уже решается библиотекой jsonschema; deterministic domain specimen и MREA measurement semantics являются продуктовой логикой.

Можно ли использовать:
YES для schema validation / NO для MREA-specific specimen orchestration.

Что используем:
- существующий CanonicalMeasurementAdapter;
- существующий MeasurementSessionService;
- Python datetime/Callable;
- jsonschema в тестах;
- canonical MREA contracts без изменений.

Что пишем сами:
- injectable clock boundary для deterministic tests;
- slice-local CapturePackage specimen с evidence frame;
- deterministic raw MeasurementPackage fixture;
- integration test, который заново строит package через реальные Chat 2 internals и требует byte-equivalent JSON semantics к committed fixture.

Почему:
Готовая библиотека не знает MREA provenance, explicit confirmation, raw anchor policy и downstream integration invariant.

Lock-in risk:
LOW. Clock и ID factories являются абстракциями через Callable; fixture использует canonical v1 wire shape.

Fallback:
Static fixture можно регенерировать тем же service + adapter flow. Если canonical v1 изменится через Chat 6, тест должен явно упасть и потребовать migration/update specimen.
```

Новые runtime dependencies не добавлены.
