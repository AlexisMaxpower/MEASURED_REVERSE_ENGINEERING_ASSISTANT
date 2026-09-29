# MREA CI Policy

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Effective from:** Pass 2

## Purpose

CI is independent execution evidence. A worker chat's statement that tests passed is not sufficient for integration acceptance when GitHub Actions can execute the same checks on a clean runner.

## Canonical workflow

`.github/workflows/ci.yml`

The workflow runs on:

- pull requests targeting `main`;
- pushes to `chat-*/pass-*` worker branches;
- manual `workflow_dispatch`.

It intentionally does not run on every direct push to `main`; worker implementation must reach `main` only after branch/PR review.

## Required jobs

- `Contracts / canonical fixtures`
- `Chat 1 / Capture`
- `Chat 2 / Measurement`
- `Chat 3 / Geometry`
- `Chat 4 / Generic CAD gate`
- `Chat 5 / Lifecycle`
- `Integration / Chat 2 -> Chat 3`

Additional cross-slice jobs are added as boundaries become executable.

## Acceptance rule

A worker pass cannot be `ACCEPTED` for integration while a required CI job for that pass is red.

Possible exceptions must be explicitly documented by Chat 6 as environment-only gates, for example a real SOLIDWORKS runtime gate that cannot execute on a GitHub-hosted runner.

## Cross-slice policy

Slice-local green tests do not imply system compatibility.

Integration tests must exercise realistic producer output, not only normalized golden fixtures. The first required boundary gate uses actual Chat 2 canonical output with `IMAGE_PX` anchors and requires Chat 3 to normalize those anchors through CapturePackage calibration into `MAT_XY_MM`.

### Expected initial state

At the moment this CI baseline is introduced, `Integration / Chat 2 -> Chat 3` is expected to be RED on the uncorrected Round 1 code. That is deliberate: CI is now reproducing the already-confirmed Round 1 integration defect. Chat 3 Pass 2 is responsible for turning this gate green without making Chat 2 falsify its raw coordinates.

## SOLIDWORKS

Generic CAD mapping/export/verification remains in GitHub-hosted CI.

Real SOLIDWORKS 2026 COM integration requires a Windows self-hosted runner or another dedicated Windows host with SOLIDWORKS installed. It is not enabled while the repository is public. This is tracked separately from the generic CAD gate.

## Branch protection target

Once required check names have appeared in GitHub Actions, `main` should be protected so pull requests cannot merge while required checks are failing.

Target required checks are the jobs listed above, except environment-only checks explicitly marked optional by Chat 6.
