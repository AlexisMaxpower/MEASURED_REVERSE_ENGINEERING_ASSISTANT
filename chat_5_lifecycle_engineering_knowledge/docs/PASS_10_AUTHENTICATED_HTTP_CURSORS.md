# Pass 10 — Authenticated HTTP Cursors

## Authorization and base

Pass 10 was started by direct user instruction after Pass 9 was frozen.

At branch start:

- `main` still pointed to Round-3 integration state;
- Chat-5 directive on `main` was still `OD-2026-09-29-003`;
- the exact frozen Pass-9 head was `07b9b768404436707575869e7188e0392a021ba5`.

Pass 10 therefore starts from that exact Pass-9 head and changes only Chat-5-owned files.

## Goal

Pass 8 made knowledge cursors deterministic, query-bound and snapshot-bound. Pass 9 exposed those cursors over HTTP, but the inner cursor checksum was only corruption detection and was not an authentication boundary.

Pass 10 adds an optional transport wrapper:

```text
mrea.knowledge-cursor.v1
→ HMAC-SHA256 authenticated envelope
→ mrea.http-cursor.v1
```

The inner cursor remains authoritative for:

- query/filter identity;
- snapshot version;
- deterministic pagination offset.

The HTTP wrapper adds authenticity for cursors crossing an untrusted transport boundary.

## Format

Authenticated cursor format:

```text
mrea.http-cursor.v1
```

The signed envelope contains:

```text
v    format version
kid  key identifier
c    inner knowledge cursor
mac  HMAC-SHA256 over canonical {v,kid,c}
```

The signing secret is never embedded in the cursor.

## Cryptographic primitive

Added `HttpCursorAuthenticator` in `src/mrea_lifecycle/http_cursor.py`.

Properties:

- HMAC-SHA256 using Python standard library;
- constant-time MAC comparison via `hmac.compare_digest()`;
- signing keys must be raw `bytes`;
- minimum key length is 32 bytes;
- key identifier must be non-empty and no longer than 128 characters;
- malformed tokens fail closed;
- unknown key identifiers fail closed;
- invalid MACs fail closed.

Public constants:

```text
HTTP_CURSOR_FORMAT_VERSION = mrea.http-cursor.v1
MIN_HTTP_CURSOR_KEY_BYTES = 32
```

## HTTP integration

`build_read_only_lifecycle_http_app()` now accepts optional cursor authentication configuration:

```python
app = build_read_only_lifecycle_http_app(
    "lifecycle.db",
    cursor_signing_key=secret_key,
    cursor_key_id="2026-09-primary",
)
```

When configured:

1. incoming external cursor is authenticated first;
2. the verified inner cursor is passed unchanged to the Pass-8 knowledge layer;
3. the knowledge layer still validates query fingerprint and snapshot version;
4. any outgoing `next_cursor` is wrapped in a new authenticated HTTP cursor.

When authentication is not configured, Pass-9 checksum-only behavior remains unchanged for local/internal deployments.

## Key rotation

The builder supports previous verification keys:

```python
app = build_read_only_lifecycle_http_app(
    "lifecycle.db",
    cursor_signing_key=new_key,
    cursor_key_id="new",
    cursor_verification_keys={
        "old": old_key,
    },
)
```

During rotation:

- old cursors signed with `old` remain verifiable;
- all newly emitted cursors use the active `new` key;
- a key-id collision with different key bytes fails closed.

This permits bounded operational rotation without weakening the current active signing key.

## Health metadata

`GET /health` now reports cursor mode:

Without signing:

```json
{
  "cursor_authentication": "checksum-only"
}
```

With signing:

```json
{
  "cursor_authentication": "hmac-sha256",
  "cursor_key_id": "2026-09-primary"
}
```

No key material is exposed.

## Security boundary

Pass 10 authenticates pagination cursors only.

It does **not** by itself make the HTTP API safe for arbitrary Internet exposure. Still outside Chat-5 scope:

- client authentication;
- authorization;
- TLS termination;
- reverse-proxy policy;
- CORS policy;
- rate limiting;
- secret provisioning/storage policy.

Those remain integration/deployment responsibilities.

## Backward compatibility

Unchanged:

- `mrea.knowledge-cursor.v1` internal format;
- query/filter fingerprint semantics;
- snapshot-version semantics;
- SQLite persistence and relational schema;
- lifecycle domain/state machine;
- CAD verification/manufacturing eligibility;
- canonical `mrea.lifecycle-event.v1`;
- direct Python knowledge APIs;
- unsigned Pass-9 HTTP mode when no signing key is supplied.

No shared contract or SQLite migration was introduced.

## Tests

Added `tests/test_http_cursor_auth.py` covering:

1. sign/verify round-trip;
2. tampered cursor rejection;
3. minimum key length/type enforcement;
4. signed HTTP pagination round-trip;
5. health metadata without exposing a key;
6. wrong-key rejection;
7. raw unsigned cursor rejection when authenticated mode is enabled;
8. previous-key acceptance during rotation;
9. re-signing with the current active key;
10. query binding retained under the authenticated wrapper;
11. snapshot staleness retained under the authenticated wrapper;
12. checksum-only mode remains backward compatible.

## Ownership

Pass 10 modifies only:

```text
chat_5_lifecycle_engineering_knowledge/
```

It does not modify:

- `core/contracts/`;
- canonical fixtures;
- `.github/workflows/`;
- `tests/integration/`;
- Chat 1-4;
- Chat 6 files.
