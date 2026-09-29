# SOLIDWORKS 2026 — Controlled Real-Host Validation / Pass 4

**Owner:** Side Chat 4B  
**Branch:** `chat-4b/pass-4`  
**Primary baseline:** `chat-4/pass-3` @ `8e5c6c503f9bf7f7420b8f6b99d71797d3073d38`  
**Latest published directive:** `OD-2026-09-29-003`

## Цель Pass 4

Закрыть незавершённую vendor-specific часть host-readiness из Pass 3 и довести путь до состояния, когда на реальном Windows 11 + SOLIDWORKS 2026 host можно одной командой получить:

1. fail-closed `mrea.cad-host-readiness.v1`;
2. собранный/найденный x64 .NET Framework CAD Agent;
3. реальный SOLIDWORKS COM run;
4. native `.SLDPRT`;
5. normalized read-back;
6. canonical CADVerificationReport;
7. `mrea.cad-runtime-evidence.v1`;
8. однозначный process exit class.

Этот документ не объявляет real-host VERIFIED: такой статус возможен только после фактического запуска на поддерживаемой машине.

## 1. Host readiness

Скрипт:

```text
scripts/test_solidworks_host_readiness.ps1
```

формирует:

```text
mrea.cad-host-readiness.v1
```

с обязательными полями каждого check:

- `code`;
- `status = PASS | FAIL | UNVERIFIED`;
- `message`;
- `required`;
- optional `details`.

Проверяются:

- `OS_WINDOWS_11_X64`;
- `PROCESS_X64`;
- `DOTNET_FRAMEWORK_48`;
- `AGENT_EXECUTABLE_AVAILABLE`;
- `SOLIDWORKS_COM_REGISTERED`;
- `SOLIDWORKS_VERSION_2026`;
- `SOLIDWORKS_INTEROP_AVAILABLE`;
- `OUTPUT_PATH_WRITABLE`;
- `PART_TEMPLATE_AVAILABLE`;
- optional `MSBUILD_AVAILABLE` при отдельном build-readiness probe.

Aggregate status вычисляется только из checks:

```text
required FAIL       -> FAILED
required UNVERIFIED -> UNVERIFIED
all required PASS   -> READY
```

Producer не может превратить неизвестный обязательный факт в READY.

## 2. SOLIDWORKS version identity

Host preflight и C# Agent используют фактический:

```text
ISldWorks::RevisionNumber()
```

Для текущего узкого baseline SOLIDWORKS 2026 ожидается revision major `34`.

Если запущена/подключена другая major revision:

- host check `SOLIDWORKS_VERSION_2026 = FAIL`;
- agent startup также fail-closes;
- transfer не считается успешным.

## 3. Part template

При явном `-PartTemplate` проверяется существование файла.

Если template не указан, readiness probe подключается к SOLIDWORKS и запрашивает:

```text
GetUserPreferenceStringValue(swDefaultTemplatePart)
```

Если default template нельзя доказать как существующий — `PART_TEMPLATE_AVAILABLE` не получает PASS.

## 4. Agent diagnostics

`mrea.solidworks-agent.v1` response расширен slice-local полями:

- `real_host_executed`;
- `solidworks_version`;
- `exit_code`;
- `diagnostics[]`;
- structured `error.code/stage/severity/details`.

Canonical contracts не изменены.

### Exit classes

```text
0   completed successfully
10  host preflight/build environment not ready (wrapper)
20  invalid request/protocol/input
30  SOLIDWORKS COM startup/version failure
40  CAD transfer/rebuild/read-back failure
50  native artifact/response persistence failure
70  unexpected internal failure
```

## 5. MSBuild discovery

`scripts/build_solidworks_agent.ps1` ищет MSBuild:

1. через `PATH`;
2. затем через Visual Studio Installer `vswhere.exe`.

Если MSBuild или official interop assemblies отсутствуют, build fail-closes и wrapper возвращает host/build-not-ready class.

## 6. One-command flow

Команда:

```powershell
cd chat_4_cad_bridge_verification

.\scripts\run_solidworks_real_host_validation.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS" `
  -OutputDir ".\artifacts\solidworks-real-host"
```

Optional:

```powershell
-PartTemplate "C:\...\Part.prtdot"
-NoAttach
-NoLaunch
-Agent "C:\...\Mrea.SolidWorksCadAgent.exe"
```

Последовательность:

```text
preliminary fail-closed host probe
-> build agent if missing
-> final host-readiness probe
-> canonical golden SketchPackage
-> Python SolidWorksAgentAdapter
-> C# x64 STA agent
-> SOLIDWORKS 2026 COM
-> native SLDPRT
-> normalized read-back
-> canonical VerificationEngine
-> CADPackage + CADVerificationReport
-> Primary Chat 4 runtime evidence builder
```

Preflight и build запускаются как отдельные PowerShell child processes, поэтому внутренний `exit` не может преждевременно завершить orchestration wrapper.

## 7. Output artifacts/evidence

Успешный controlled run должен оставить минимум:

```text
host_readiness.json
<sketch_package_id>.SLDPRT
cad_package.json
cad_verification.json
runtime_evidence.json
```

Если agent отсутствовал до запуска, также может быть:

```text
host_readiness_prebuild.json
```

## 8. Runtime VERIFIED

`REAL_HOST_GATE=VERIFIED` печатается только если Primary Chat 4 `build_runtime_evidence()` возвращает:

```text
status = VERIFIED
```

То есть недостаточно:

- просто запустить SOLIDWORKS;
- просто сохранить SLDPRT;
- получить generic CADVerificationReport = VERIFIED без real-host evidence.

Нужны READY host facts, actual SOLIDWORKS version, native artifact SHA-256, read-back и canonical verification.

## 9. Текущее состояние проверки

В ChatGPT execution environment отсутствуют:

- Windows 11 host;
- PowerShell runtime;
- .NET Framework/MSBuild toolchain;
- SOLIDWORKS 2026;
- official SOLIDWORKS interop assemblies.

Поэтому:

```text
C# COMPILE = UNVERIFIED
REAL_HOST = UNVERIFIED
```

Pure/static проверки выполняются отдельно; они не заменяют real-host gate.

## 10. Integration note для Primary Chat 4

Primary `SubprocessSolidWorksAgentRunner`/`parse_solidworks_agent_response()` сейчас корректно игнорирует новые backward-compatible response fields, но не переносит stable agent diagnostic code/exit_code/solidworks_version в `CadAdapterResult`.

Pass 4 не меняет Primary-owned Python semantics. Для более полного propagation Primary Chat 4 может позже добавить slice-local metadata/diagnostic transport без изменения canonical contracts.
