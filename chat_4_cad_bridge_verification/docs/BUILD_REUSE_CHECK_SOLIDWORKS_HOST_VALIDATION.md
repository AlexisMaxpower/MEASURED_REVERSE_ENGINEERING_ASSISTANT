# BUILD / REUSE CHECK — SOLIDWORKS Host Validation

**Chat:** Side Chat 4B  
**Pass:** 4  
**Latest published orchestrator directive available:** `OD-2026-09-29-003`

## Проблема

Нужно достоверно отличать:

- обычный generic/test-double CAD gate;
- готовность конкретного Windows/SOLIDWORKS host;
- фактически выполненный real-host run.

До этого SOLIDWORKS Agent мог быть запущен вручную, но отсутствовал единый fail-closed host preflight с machine-readable причинами и стабильными exit-классами.

## Есть ли готовое open-source решение

PARTIAL.

Стандартные механизмы Windows/.NET/SOLIDWORKS уже дают необходимые факты:

- PowerShell / CIM — Windows identity;
- .NET registry — наличие .NET Framework 4.8;
- COM registration / `SldWorks.Application` — доступность SOLIDWORKS automation;
- SOLIDWORKS `ISldWorks::RevisionNumber()` — фактическая версия запущенного/probed приложения;
- SOLIDWORKS user preference API — default part template;
- Visual Studio Installer `vswhere` — поиск MSBuild;
- filesystem probe — проверка writable artifact directory;
- существующий Primary Chat 4 `mrea.cad-host-readiness.v1` parser и `mrea.cad-runtime-evidence.v1` builder.

## Можно ли использовать

YES / PARTIAL.

## Что используем

- Windows PowerShell 5.1-compatible primitives;
- `Get-CimInstance Win32_OperatingSystem`;
- `.NET Framework Setup\NDP\v4\Full\Release`;
- `Type.GetTypeFromProgID("SldWorks.Application")`;
- `Marshal.GetActiveObject` / explicit COM launch only when allowed;
- `ISldWorks::RevisionNumber()`;
- `ISldWorks::GetUserPreferenceStringValue(swDefaultTemplatePart)`;
- official local `SolidWorks.Interop.*` assemblies;
- `vswhere.exe` fallback for MSBuild discovery;
- Primary Chat 4 readiness/evidence parsing and aggregation.

## Что пишем сами

- deterministic MREA host-readiness orchestration;
- stable readiness codes/statuses/messages/details;
- fail-closed aggregate production compatible with Primary Chat 4 parser;
- process exit-class mapping;
- one-command controlled real-host procedure;
- adapter response diagnostics and actual SOLIDWORKS revision recording;
- linkage from readiness → canonical golden transfer → runtime evidence.

## Почему

Готовые Windows/SOLIDWORKS APIs дают низкоуровневые факты, но не дают MREA-specific доказательство того, что конкретный CAD run:

1. произошёл на поддерживаемом host;
2. использовал поддерживаемую SOLIDWORKS version;
3. создал native artifact;
4. прошёл canonical numerical read-back verification;
5. сохранил evidence chain без silent success.

Эта orchestration logic — часть уникальной проверяемости MREA.

## Lock-in risk

Medium.

Windows/COM/SOLIDWORKS-specific probe находится только в Side Chat 4B-owned scripts/agent. Canonical contracts и Primary verification semantics остаются vendor-neutral.

## Fallback

Если PowerShell/COM probe не может доказать обязательный факт, check получает `UNVERIFIED` или `FAIL`; host не становится READY. Ручная подмена результата на PASS не предусмотрена.
