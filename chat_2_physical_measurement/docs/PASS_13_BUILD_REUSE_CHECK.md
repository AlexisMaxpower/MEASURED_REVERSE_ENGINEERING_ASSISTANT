# PASS 13 — BUILD / REUSE CHECK

**Проблема:** текущий `InMemoryMeasurementSessionRepository` теряет pending/confirmed measurement session при завершении процесса, что противоречит offline-first требованию Chat 2: session/evidence/pending measurements не должны исчезать при interruption.

**Есть ли готовое open-source решение:** YES. Python standard library уже включает SQLite (`sqlite3`) с transactional local persistence.

**Можно ли использовать:** YES.

**Что используем:** Python stdlib `sqlite3` как durable storage engine; существующие Chat-2 domain models как source of truth; versioned private JSON payload внутри локальной таблицы.

**Что пишем сами:** `MeasurementSessionRepository` Protocol, Chat-2 codec domain model <-> private local payload, `SqliteMeasurementSessionRepository`, fail-closed schema/corruption handling и regression tests.

**Почему:** не требуется писать собственный storage engine или добавлять внешнюю ORM/DB dependency. SQLite закрывает atomic transaction/durability baseline и работает offline. JSON payload остаётся локальной implementation detail и не становится shared/canonical contract.

**Lock-in risk:** LOW. Application service зависит от repository Protocol, поэтому SQLite можно позже заменить другим local/project repository без изменения measurement domain flow.

**Fallback:** `InMemoryMeasurementSessionRepository` остаётся доступным для unit tests/ephemeral workflows. Неизвестная версия persisted schema или повреждённый payload fail-closed и не превращаются в measurement truth.
