# PASS 15 — BUILD / REUSE CHECK

**Проблема:** Pass 14 умеет детерминированно перечислять сохранённые `MeasurementSession`, но SQLite backend декодирует весь набор строк. Для больших локальных наборов нужен bounded keyset traversal без `OFFSET` и без full-table payload decode на каждый page request.

**Есть ли готовое open-source решение:** YES/PARTIAL. SQLite уже предоставляет составные индексы, range predicates и transactional schema migration primitives. Отдельная ORM/pagination библиотека для этого локального query surface не нужна.

**Можно ли использовать:** YES.

**Что используем:** существующий `MeasurementSessionRepository`, stdlib SQLite, Pass-13/14 private payload `mrea.chat2.measurement-session.local.v1`, составные SQLite индексы и deterministic keyset ordering.

**Что пишем сами:** `MeasurementSessionPageCursor`, `MeasurementSessionPage`, `list_session_page(...)`, page/cursor validation, project-scope binding, UTC-microsecond index metadata, backward-compatible metadata backfill старых БД и fail-closed metadata/payload consistency validation.

**Почему:** keyset pagination избегает деградации `OFFSET` при росте таблицы и сохраняет уже принятую сортировку `created_at DESC, session_id ASC`. Индексные metadata являются private storage implementation detail; canonical/shared contracts и payload schema не меняются.

**Lock-in risk:** LOW. Cursor/page semantics находятся на repository boundary и одинаковы для in-memory/SQLite backend. SQLite-specific columns/indexes остаются внутри durable adapter.

**Fallback:** существующий `list_sessions(...)` остаётся совместимым и теперь может проходить durable store bounded pages. Если legacy payload повреждён, schema version неизвестна или indexed metadata расходятся с decoded truth, операция fail-closed вместо пропуска/искажения measurement session.
