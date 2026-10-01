# PASS 4 — BUILD / REUSE CHECK

**Problem:** Chat 2 hard-coded `unit="mm"` for all measurement types, which makes `ANGLE` semantically wrong at the application boundary.

**Есть ли готовое open-source решение:** Generic units libraries exist, but this problem is not unit conversion. It is a small closed domain mapping already defined by the canonical MREA contract (`mm` for length-like measurements, `deg` for angles).

**Можно ли использовать:** NO for the domain registry itself.

**Что используем:** Python standard library only; existing canonical `MeasurementType` enum and wire contract values.

**Что пишем сами:** `MeasurementTypeRegistry` and immutable `MeasurementTypeSemantics`.

**Почему:** The registry contains only MREA-owned domain semantics for the 11 canonical measurement types. A third-party units framework would add dependency and conversion behavior without solving the ownership problem.

**Lock-in risk:** LOW. The registry is a tiny internal abstraction with string units already required by canonical v1.

**Fallback:** Remove the registry and inline the canonical mapping in the application service if the abstraction proves unnecessary; wire output remains unchanged.
