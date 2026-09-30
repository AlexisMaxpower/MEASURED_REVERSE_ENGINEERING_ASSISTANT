# PASS 5 — BUILD / REUSE CHECK

**Проблема:** внутреннее поле `uncertainty_mm` жёстко кодирует миллиметры и после Pass 4 становится семантически неверным для `ANGLE`, где единица измерения — `deg`.

**Есть ли готовое open-source решение:** generic units/quantities libraries существуют, но здесь не нужна конвертация единиц или dimensional-analysis engine. Нужно согласовать уже существующую MREA domain model с canonical wire field `uncertainty`.

**Можно ли использовать:** NO для самой миграции domain semantics.

**Что используем:** Python standard library, существующий `MeasurementTypeRegistry`, существующий canonical `MeasurementPackage.uncertainty`.

**Что пишем сами:** unit-neutral internal `uncertainty`, compatibility bridge для старого `uncertainty_mm`, fail-closed rules и regression tests.

**Почему:** это малая внутренняя миграция модели данных. Добавление сторонней units-библиотеки увеличило бы dependency surface и не решило бы backward compatibility старых Chat 2 вызовов.

**Lock-in risk:** LOW. Основное поле теперь совпадает по смыслу с canonical contract; legacy alias локализован внутри Chat 2.

**Fallback:** если legacy bridge больше не нужен после миграции всех callers, удалить `uncertainty_mm` отдельным breaking cleanup pass, оставив `uncertainty` без изменения wire contract.
