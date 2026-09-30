# ORCHESTRATOR HANDOFF — Chat 5 / Pass 10

**Authorization:** direct user instruction to continue development  
**Orchestrator status at branch start:** no newer Chat-5-specific directive was present on `main`; `ORCHESTRATOR_DIRECTIVE.md` still reported `OD-2026-09-29-003`  
**Branch:** `chat-5/pass-10`  
**Base SHA:** `07b9b768404436707575869e7188e0392a021ba5` — frozen Chat 5 Pass 9  
**Documented pre-handoff SHA:** `a9fb3831be27a3ed2b3ee920708cf6bad6ce1db5`  
**Pre-handoff CI run:** `36659195203`  
**Status at handoff:** required Chat 5 gates GREEN

> This handoff is the final worker commit and freezes `chat-5/pass-10`. Chat 6 should use the current branch head as the final handoff commit. The documented pre-handoff SHA above is the exact implementation/documentation state exercised by the required gates.

## 1. Delivered functionality

Pass 10 adds optional **HMAC-SHA256 authentication for HTTP pagination cursors** without replacing the existing Pass-8 knowledge cursor semantics.

Cursor chain:

```text
mrea.knowledge-cursor.v1
→ HMAC-SHA256 authenticated HTTP envelope
→ mrea.http-cursor.v1
```

The inner knowledge cursor remains responsible for deterministic pagination, query/filter identity and snapshot binding. The new outer cursor proves that the cursor was issued by a holder of an accepted HTTP cursor key.

## 2. Authenticated cursor format

New transport format:

```text
mrea.http-cursor.v1
```

Envelope fields:

```text
v    format version
kid  key identifier
c    inner mrea.knowledge-cursor.v1
mac  HMAC-SHA256 over canonical {v,kid,c}
```

Key material is never serialized into the cursor.

## 3. New authentication primitive

Added `src/mrea_lifecycle/http_cursor.py` with:

- `HttpCursorAuthenticator`;
- `LifecycleHttpCursorError`;
- `HTTP_CURSOR_FORMAT_VERSION`;
- `MIN_HTTP_CURSOR_KEY_BYTES = 32`.

Security properties:

- HMAC-SHA256 from Python stdlib;
- `hmac.compare_digest()` for constant-time MAC comparison;
- signing key must be raw `bytes`;
- minimum signing-key length is 32 bytes;
- key IDs are validated and bounded;
- malformed envelopes fail closed;
- unknown key IDs fail closed;
- invalid MACs fail closed;
- active key ID cannot conflict with a different verification key.

## 4. HTTP integration

`ReadOnlyLifecycleHttpAPI` now accepts an optional cursor authenticator.

`build_read_only_lifecycle_http_app()` now supports:

```python
build_read_only_lifecycle_http_app(
    database,
    cursor_signing_key=secret_key,
    cursor_key_id="primary",
    cursor_verification_keys={"previous": old_key},
)
```

Authenticated request flow:

```text
external signed cursor
→ verify mrea.http-cursor.v1 HMAC
→ extract inner knowledge cursor
→ existing Pass-8 query/snapshot validation
→ execute deterministic query
→ obtain inner next_cursor
→ sign with active HTTP key
→ return authenticated next_cursor
```

The HTTP layer does not decode or reinterpret the internal knowledge cursor state.

## 5. Key rotation

Previous keys can remain in `cursor_verification_keys` during a rotation window.

Behavior:

- cursor signed by a previous accepted key is still readable;
- new cursors are always signed with the active key ID;
- removed/unknown key IDs fail closed;
- active-key conflicts are rejected during configuration.

This supports deterministic rotation without persisting cursor state server-side.

## 6. Health metadata

`GET /health` reports the active cursor transport mode.

Without signing:

```text
cursor_authentication = checksum-only
```

With signing:

```text
cursor_authentication = hmac-sha256
cursor_key_id = <active key id>
```

No signing or verification key bytes are exposed.

## 7. Backward compatibility

Unchanged:

- `mrea.knowledge-cursor.v1` internal format;
- query/filter fingerprint semantics;
- snapshot-version semantics;
- direct Python knowledge APIs;
- SQLite persistence/relational schemas;
- lifecycle state machine;
- CAD verification/manufacturing eligibility;
- canonical `mrea.lifecycle-event.v1`;
- Pass-9 checksum-only HTTP behavior when no signing key is configured.

No shared contract change and no SQLite migration were required.

## 8. Files changed in Pass 10

Added:

- `src/mrea_lifecycle/http_cursor.py`;
- `tests/test_http_cursor_auth.py`;
- `docs/PASS_10_AUTHENTICATED_HTTP_CURSORS.md`.

Modified:

- `src/mrea_lifecycle/http_api.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md`.

No Pass-10 file outside `chat_5_lifecycle_engineering_knowledge/` was modified.

## 9. Deterministic tests

`tests/test_http_cursor_auth.py` verifies:

1. authenticated cursor sign/verify round-trip;
2. tampered token rejection;
3. minimum 32-byte key enforcement;
4. binary key-type enforcement;
5. signed HTTP pagination round-trip;
6. authenticated health metadata;
7. wrong/unknown key rejection;
8. raw unsigned cursor rejection when authenticated mode is enabled;
9. old-key acceptance during rotation;
10. re-signing with the active key;
11. original query/filter binding remains enforced;
12. original snapshot staleness remains enforced;
13. checksum-only HTTP mode remains backward compatible.

## 10. Independent CI evidence

Documented pre-handoff SHA:

```text
a9fb3831be27a3ed2b3ee920708cf6bad6ce1db5
```

Workflow:

```text
MREA CI / 36659195203
```

Chat 5 result:

```text
53 passed in 2.54s
```

Required results:

- `Chat 5 / Lifecycle` — **SUCCESS**;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**.

Earlier intermediate workflow runs were cancelled by the repository's `cancel-in-progress: true` concurrency policy after later Pass-10 commits; they are not treated as test evidence.

## 11. Ownership verification

Pre-handoff diff against frozen Pass 9 base `07b9b768404436707575869e7188e0392a021ba5` contained exactly seven files, all under Chat 5 ownership.

This handoff is the eighth changed file.

No Pass-10 changes were made to:

- `core/contracts/`;
- canonical fixtures;
- `.github/workflows/`;
- `tests/integration/`;
- Chat 1-4;
- Chat 6 files.

## 12. Security boundary

Pass 10 authenticates pagination cursors only.

It does not provide:

- client/user authentication;
- authorization;
- TLS termination;
- reverse-proxy hardening;
- CORS policy;
- rate limiting;
- secret provisioning/storage.

The API must therefore still be treated as a local/internal transport until those deployment controls are defined by the owning integration layer.

## 13. Remaining known limitations

Still intentionally open:

- keyset pagination for very large histories;
- materialized analytical aggregates;
- semantic/AI interpretation;
- field-device synchronization;
- framework-specific application shell and deployment configuration.

## 14. Open Change Requests

None.

Pass 10 required no shared-contract change.

## 15. Requested acceptance gate

Please verify:

1. HMAC wrapper does not replace or weaken inner query/snapshot binding;
2. tampered/wrong-key/unknown-key cursors fail closed;
3. key rotation accepts previous keys but emits only with the active key;
4. key material is not serialized;
5. checksum-only Pass-9 mode remains backward compatible;
6. direct Python APIs and SQLite schemas remain unchanged;
7. canonical lifecycle/CAD eligibility behavior remains unchanged;
8. required CI gates are green;
9. ownership boundaries are preserved;
10. Chat 6 reconciles the direct-user Pass-10 branch base during central integration.

Requested verdict: **Pass 10 ACCEPTED, ACCEPTED_WITH_REBASE/INTEGRATION FOLLOWUP, or explicit FIX_REQUIRED.**
