# MREA CI Setup

The repository CI is defined in `.github/workflows/ci.yml`.

## Automatic triggers

- pull request targeting `main`;
- push to `chat-*/pass-*`;
- manual workflow dispatch.

## What CI currently verifies

1. canonical schemas and fixtures;
2. Chat 1 tests;
3. Chat 2 tests;
4. Chat 3 tests;
5. Chat 4 generic CAD tests;
6. Chat 5 tests;
7. real Chat 2 → Chat 3 integration boundary.

## Branch protection

After GitHub has recorded the required check names at least once, configure `main` in repository Settings → Rules / Rulesets (or Branches / branch protection, depending on GitHub UI):

- require a pull request before merging;
- require status checks to pass;
- require the MREA CI checks used by Chat 6;
- prevent worker branches from bypassing these gates.

Chat 6 currently cannot apply repository-administration rules through the available connector, so this final repository-setting toggle must be performed in GitHub UI by the repository owner.

## SOLIDWORKS

Real SOLIDWORKS 2026 COM integration is not executed on the public GitHub-hosted runner. It will require a controlled Windows self-hosted runner or equivalent dedicated host later.
