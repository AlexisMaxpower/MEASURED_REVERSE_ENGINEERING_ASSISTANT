# Chat 4 — Runtime Evidence / Host Readiness v1

**Pass:** 3  
**Directive:** `OD-2026-09-29-003`  
**Scope:** slice-local Chat 4 protocol; **not** a canonical shared contract.

## Purpose

Separate three different truths that must never be conflated:

1. canonical numerical CAD verification;
2. host readiness for the SOLIDWORKS worker;
3. evidence that a real Windows + SOLIDWORKS execution actually happened.

A canonical `CADVerificationReport.overall_status = VERIFIED` is not, by itself, proof that the real SOLIDWORKS host ran.

## Host readiness model

Schema identifier:

`mrea.cad-host-readiness.v1`

Each check has:

- `code`;
- `status = PASS | FAIL | UNVERIFIED`;
- `message`;
- `required`;
- optional `details`.

Primary Chat 4 recomputes aggregate readiness:

- any required `FAIL` -> `FAILED`;
- otherwise any required `UNVERIFIED` -> `UNVERIFIED`;
- all required `PASS` -> `READY`.

A producer-provided aggregate status that disagrees with the checks is rejected.

## Required Side Chat 4B checks

At minimum where technically applicable:

- `OS_WINDOWS_11_X64`;
- `PROCESS_X64`;
- `DOTNET_FRAMEWORK_48`;
- `AGENT_EXECUTABLE_AVAILABLE`;
- `SOLIDWORKS_COM_REGISTERED`;
- `SOLIDWORKS_VERSION_2026`;
- `SOLIDWORKS_INTEROP_AVAILABLE`;
- `OUTPUT_PATH_WRITABLE`;
- `PART_TEMPLATE_AVAILABLE` when no usable default exists.

Unknown required facts are `UNVERIFIED`, never `PASS`.

## Runtime evidence model

Schema identifier:

`mrea.cad-runtime-evidence.v1`

It records:

- `VERIFIED | FAILED | UNVERIFIED` runtime status;
- adapter identity;
- whether a real host actually executed;
- SOLIDWORKS version;
- input `sketch_package_id`;
- generated `cad_package_id`;
- host-readiness report;
- native artifact metadata/hash;
- normalized read-back dimensions;
- canonical verification report;
- machine-readable diagnostics.

## VERIFIED conditions

Runtime evidence becomes `VERIFIED` only when all are true:

1. real host execution is explicitly recorded;
2. host readiness is `READY`;
3. SOLIDWORKS version is present;
4. CAD transfer execution exists;
5. canonical verification report is `VERIFIED`;
6. at least one `SOLIDWORKS_PART` artifact has non-empty identity/URI and valid SHA-256;
7. read-back values/units agree with verification items;
8. SketchPackage/CADPackage/report/adapter identities agree;
9. no ERROR diagnostic remains.

If the real host did not run, runtime status is always `UNVERIFIED`, even if generic numerical verification succeeded.

## Identity protections

Evidence construction rejects:

- SketchPackage identity drift;
- adapter identity drift;
- CADPackage/report linkage drift;
- CADPackage artifacts differing from adapter-result artifacts;
- verification actual values without matching normalized read-back.

## Failure diagnostics

Diagnostics are slice-local objects with:

- `code`;
- `stage`;
- `message`;
- `severity = ERROR | WARNING | INFO`;
- optional `details`.

Stable codes are preferred over parsing text messages.

## Ownership

Primary Chat 4 owns readiness/evidence semantics and generic validation. Side Chat 4B owns Windows/.NET/SOLIDWORKS/COM probes, native artifact generation, real-host execution, and process exit codes.

Neither side changes canonical shared contracts for this protocol.
