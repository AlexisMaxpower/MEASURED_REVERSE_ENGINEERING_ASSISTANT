# BUILD / REUSE CHECK — Chat 1 Phase 2

**Дата:** 2026-09-29  
**Scope:** Manual capture baseline, local artifacts, camera metadata, capture-session persistence.

## Artifact storage

**Проблема:** offline capture должен сохранять frame bytes надёжно, не теряя связь с metadata и checksum.

**Есть ли готовое open-source решение:** object storage systems существуют, но cloud/object-storage dependency запрещена для offline capture baseline.

**Можно ли использовать:** PARTIAL.

**Что используем:** standard library `hashlib`, `pathlib`, `os.replace`.

**Что пишем сами:** тонкий `ArtifactStore` protocol и `FileSystemArtifactStore` adapter.

**Почему:** хранение bytes — инфраструктурная задача, но Chat 1 нужен local-only adapter уже в R1. Content-addressed path по SHA-256 упрощает integrity verification и исключает зависимость от внешнего сервиса.

**Lock-in risk:** низкий; application layer зависит от `ArtifactStore`, а не от filesystem.

**Fallback:** adapter к object storage/local mobile storage после решения Integrator/мобильной архитектуры.

## Capture session persistence

**Проблема:** offline workflow должен переживать restart приложения и сохранять frame metadata/state.

**Есть ли готовое open-source решение:** да, SQLite/ORM, key-value/mobile databases.

**Можно ли использовать:** PARTIAL — repository-wide persistence ещё не утверждена.

**Что используем:** тот же internal atomic JSON repository pattern, что в Phase 1.

**Что пишем сами:** `CaptureSessionRepository` protocol + `JsonCaptureSessionRepository` adapter.

**Почему:** semantics и state machine можно реализовать и протестировать сейчас, не принимая глобальное DB-решение за Integrator.

**Lock-in risk:** низкий.

**Fallback:** SQLite/SQLAlchemy/mobile DB adapter без изменения `CaptureSessionService`.

## Image processing

**Проблема:** Phase 2 должен различать clean reference и measurement frames, но не обязан выполнять CV.

**Есть ли готовое open-source решение:** OpenCV и platform camera APIs.

**Можно ли использовать:** YES later.

**Что используем сейчас:** ничего; Phase 2 принимает уже полученные image bytes + camera metadata.

**Что пишем сами:** capture workflow/state rules и provenance-like internal frame records.

**Почему:** camera/CV implementation относится к следующим фазам; подключение OpenCV здесь добавило бы зависимость без задачи.

**Lock-in risk:** отсутствует.

**Fallback:** OpenCV/native camera adapters в Phase 3/4.
