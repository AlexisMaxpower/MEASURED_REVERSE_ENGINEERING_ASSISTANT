# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-30**
- Branch: `chat-5/pass-10`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Pass 10 authorization: **direct user instruction; no newer Chat-5-specific directive present on `main` at branch start**
- Base SHA: `07b9b768404436707575869e7188e0392a021ba5` (frozen Chat 5 Pass 9)
- State: **authenticated HTTP cursors implemented; final CI/cross-slice gates and handoff pending**

## Preserved baseline

Still active and unchanged:

- Revision / Manufacturing / Installation / Test / Failure domain;
- canonical CADPackage + CADVerificationReport transfer;
- VERIFIED manufacturing eligibility gate;
- canonical `LifecycleEvent v1` adapter;
- physical-instance state machine;
- exact instance/evidence linkage;
- equipment/position occupancy protection;
- removal/replacement/supersession semantics;
- LifecycleRepository + LifecycleUnitOfWork;
- authoritative SQLite snapshot;
- normalized relational read model and migrations;
- SQL-native lifecycle queries;
- verified backup/restore;
- read-only SQLite query session;
- deterministic engineering knowledge queries;
- snapshot-bound knowledge pagination;
- Pass-9 GET-only HTTP/API transport.

No shared contract, canonical fixture, CI workflow, integration test, SQLite migration, or other chat-owned file was changed.

## Pass 10 additions

### Authenticated HTTP cursor primitive

Added `src/mrea_lifecycle/http_cursor.py`.

Public surface:

- `HttpCursorAuthenticator`;
- `LifecycleHttpCursorError`;
- `HTTP_CURSOR_FORMAT_VERSION = mrea.http-cursor.v1`;
- `MIN_HTTP_CURSOR_KEY_BYTES = 32`.

The authenticator wraps the existing Pass-8 knowledge cursor rather than replacing it.

### Authentication model

Authenticated envelope fields:

```text
v    cursor format
kid  key identifier
c    inner knowledge cursor
mac  HMAC-SHA256(v,kid,c)
```

The MAC is computed over canonical JSON with sorted keys and compact separators.

Verification uses `hmac.compare_digest()`.

### Key validation

Fail-closed configuration rules:

- signing key must be `bytes`;
- signing key must be at least 32 bytes;
- key ID must be a non-empty string;
- key ID length is limited to 128 characters;
- active key ID cannot map to conflicting verification-key bytes.

### HTTP integration

`ReadOnlyLifecycleHttpAPI` now accepts an optional `HttpCursorAuthenticator`.

`build_read_only_lifecycle_http_app()` adds:

```python
cursor_signing_key: bytes | None
cursor_key_id: str = "default"
cursor_verification_keys: Mapping[str, bytes] | None
```

Authenticated mode flow:

```text
external signed cursor
→ HMAC verification
→ inner mrea.knowledge-cursor.v1
→ existing query/snapshot validation
→ query execution
→ inner next_cursor
→ HMAC signing with active key
→ external signed cursor
```

### Key rotation

Previous keys may be supplied through `cursor_verification_keys`.

A cursor signed with a previous key remains accepted while that key ID is in the verification map. Every newly emitted cursor is signed with the current active key.

### Health metadata

Without authenticated mode:

```text
cursor_authentication = checksum-only
```

With authenticated mode:

```text
cursor_authentication = hmac-sha256
cursor_key_id = <active key id>
```

No secret key material is serialized.

## Backward compatibility

Pass 10 is additive.

Unchanged:

- direct Python lifecycle queries;
- direct engineering knowledge queries;
- `mrea.knowledge-cursor.v1` inner format;
- query/filter binding;
- snapshot-version binding;
- persistence and relational schemas;
- lifecycle state transitions;
- CAD verification/manufacturing eligibility;
- canonical shared contracts;
- checksum-only Pass-9 HTTP mode when no signing key is configured.

## Verification

### New tests

Added `tests/test_http_cursor_auth.py`.

Coverage verifies:

1. HMAC sign/verify round-trip;
2. tampered token rejection;
3. minimum signing-key length;
4. binary key-type enforcement;
5. signed HTTP pagination round-trip;
6. authenticated health metadata;
7. wrong-key / unknown-key rejection;
8. rejection of raw unsigned cursor when authenticated mode is active;
9. previous-key acceptance during rotation;
10. re-signing with the current active key;
11. preservation of query binding;
12. preservation of snapshot staleness detection;
13. checksum-only mode backward compatibility.

### Required final gates

Before handoff, verify on the documented pre-handoff SHA:

- `Chat 5 / Lifecycle`;
- `Contracts / canonical fixtures`;
- `Chat 4 / Generic CAD gate`;
- `Integration / Chat 4 -> Chat 5`.

## Files added in Pass 10

- `src/mrea_lifecycle/http_cursor.py`;
- `tests/test_http_cursor_auth.py`;
- `docs/PASS_10_AUTHENTICATED_HTTP_CURSORS.md`.

## Files modified in Pass 10

- `src/mrea_lifecycle/http_api.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Security limitations

Cursor authentication does not provide:

- user/client authentication;
- authorization;
- TLS;
- reverse-proxy hardening;
- CORS policy;
- rate limiting;
- secure secret provisioning/storage.

Those are required before arbitrary remote Internet exposure and are owned by the future integration/deployment layer.

## Other known limitations

Still open:

- keyset pagination for very large histories;
- materialized analytical aggregates;
- semantic/AI interpretation;
- field-device synchronization.

## Handoff rule

After `ORCHESTRATOR_HANDOFF.md` is published as the final worker commit, `chat-5/pass-10` is frozen. No later commit is allowed unless final verification finds a real missing/incorrect GitHub file or Chat 6 explicitly requests a correction.
