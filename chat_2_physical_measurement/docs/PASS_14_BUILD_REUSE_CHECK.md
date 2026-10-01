# PASS 14 — BUILD / REUSE CHECK

**Проблема:** после Pass 13 durable `MeasurementSession` можно сохранить и открыть по известному `session_id`, но нет локального API перечисления сохранённых сессий и выборки по `project_id`.

**Есть ли готовое open-source решение:** PARTIAL. SQLite уже предоставляет хранение и выборку строк, а Python standard library — всё необходимое для текущего объёма. Отдельная query/ORM библиотека для простого перечисления сессий не нужна.

**Можно ли использовать:** YES.

**Что используем:** существующий Pass-13 `MeasurementSessionRepository` boundary, stdlib SQLite и текущий versioned private local payload `mrea.chat2.measurement-session.local.v1`.

**Что пишем сами:** минимальный `list_sessions(project_id=...)` contract внутри Chat-2 repository Protocol, одинаковую семантику для in-memory/SQLite backend, deterministic newest-first ordering, project filter normalization и fail-closed decoding.

**Почему:** это закрывает явный remaining debt Pass 13 без изменения shared contracts, без schema migration и без новой dependency. Фильтрация выполняется по уже сохранённому private payload; прежние SQLite базы Pass 13 остаются читаемыми без ALTER TABLE.

**Lock-in risk:** LOW. Application service зависит от repository Protocol; query semantics не зависят от SQLite-specific API.

**Fallback:** `get(session_id)` остаётся неизменным. Если persisted row повреждён или имеет неподдерживаемую private schema version, enumeration fail-closed вместо пропуска/скрытия повреждённой measurement truth.
