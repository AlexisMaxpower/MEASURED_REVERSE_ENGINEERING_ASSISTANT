from datetime import datetime, timedelta, timezone
import json
from urllib.parse import urlencode

import pytest

from mrea_lifecycle import (
    HttpCursorAuthenticator,
    LifecycleHttpCursorError,
    LifecycleUnitOfWork,
    Revision,
    SQLiteLifecycleStore,
    build_read_only_lifecycle_http_app,
)


T0 = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
OLD_KEY = b"o" * 32
NEW_KEY = b"n" * 32
OTHER_KEY = b"x" * 32


def _seed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        previous = None
        for index in range(1, 4):
            revision_id = f"R{index}"
            uow.revisions.create(
                Revision(
                    revision_id,
                    "PART-AUTH",
                    f"REV{index:02d}",
                    T0 + timedelta(minutes=index),
                    parent_revision_id=previous,
                ),
                event_id=f"LC-{revision_id}",
            )
            previous = revision_id
    store.close()


def _request(app, path: str, params: dict[str, object] | None = None):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    query = urlencode(params or {})
    chunks = app(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "QUERY_STRING": query,
        },
        start_response,
    )
    body = b"".join(chunks)
    return int(captured["status"].split()[0]), json.loads(body.decode("utf-8"))


def test_http_cursor_authenticator_signs_verifies_and_rejects_tampering() -> None:
    authenticator = HttpCursorAuthenticator(OLD_KEY, key_id="old")
    token = authenticator.sign("inner-cursor")

    assert token != "inner-cursor"
    assert authenticator.verify(token) == "inner-cursor"

    replacement = "A" if token[-1] != "A" else "B"
    tampered = token[:-1] + replacement
    with pytest.raises(LifecycleHttpCursorError):
        authenticator.verify(tampered)


def test_http_cursor_authenticator_requires_strong_binary_key() -> None:
    with pytest.raises(LifecycleHttpCursorError, match="at least 32 bytes"):
        HttpCursorAuthenticator(b"too-short")
    with pytest.raises(LifecycleHttpCursorError, match="must be bytes"):
        HttpCursorAuthenticator("not-bytes")  # type: ignore[arg-type]


def test_signed_http_cursor_round_trip_and_health_metadata(tmp_path) -> None:
    database = tmp_path / "signed.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=OLD_KEY,
        cursor_key_id="old",
    )

    status, health = _request(app, "/health")
    assert status == 200
    assert health["data"]["cursor_authentication"] == "hmac-sha256"
    assert health["data"]["cursor_key_id"] == "old"

    status, first = _request(
        app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1},
    )
    assert status == 200
    assert first["data"]["items"][0]["revision_id"] == "R1"
    cursor = first["data"]["next_cursor"]
    assert isinstance(cursor, str)
    assert HttpCursorAuthenticator(OLD_KEY, key_id="old").verify(cursor)

    status, second = _request(
        app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1, "cursor": cursor},
    )
    assert status == 200
    assert second["data"]["items"][0]["revision_id"] == "R2"


def test_wrong_key_and_unsigned_cursor_are_rejected_when_authentication_enabled(
    tmp_path,
) -> None:
    database = tmp_path / "wrong-key.db"
    _seed_database(database)

    old_app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=OLD_KEY,
        cursor_key_id="old",
    )
    _, first = _request(
        old_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1},
    )
    signed_cursor = first["data"]["next_cursor"]

    wrong_app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=OTHER_KEY,
        cursor_key_id="other",
    )
    status, wrong = _request(
        wrong_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1, "cursor": signed_cursor},
    )
    assert status == 400
    assert "key_id" in wrong["error"]["message"]

    unsigned_app = build_read_only_lifecycle_http_app(database)
    _, unsigned_first = _request(
        unsigned_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1},
    )
    raw_cursor = unsigned_first["data"]["next_cursor"]
    status, unsigned_rejected = _request(
        old_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1, "cursor": raw_cursor},
    )
    assert status == 400
    assert "HTTP cursor" in unsigned_rejected["error"]["message"]


def test_key_rotation_accepts_previous_key_and_resigns_with_active_key(tmp_path) -> None:
    database = tmp_path / "rotation.db"
    _seed_database(database)

    old_app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=OLD_KEY,
        cursor_key_id="old",
    )
    _, first = _request(
        old_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1},
    )
    old_cursor = first["data"]["next_cursor"]

    rotated_app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=NEW_KEY,
        cursor_key_id="new",
        cursor_verification_keys={"old": OLD_KEY},
    )
    status, second = _request(
        rotated_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1, "cursor": old_cursor},
    )
    assert status == 200
    assert second["data"]["items"][0]["revision_id"] == "R2"
    new_cursor = second["data"]["next_cursor"]
    assert new_cursor is not None

    new_authenticator = HttpCursorAuthenticator(
        NEW_KEY,
        key_id="new",
        verification_keys={"old": OLD_KEY},
    )
    assert new_authenticator.verify(new_cursor)
    with pytest.raises(LifecycleHttpCursorError, match="unknown HTTP cursor key_id"):
        HttpCursorAuthenticator(OLD_KEY, key_id="old").verify(new_cursor)


def test_authenticated_cursor_preserves_query_and_snapshot_binding(tmp_path) -> None:
    database = tmp_path / "binding.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=OLD_KEY,
        cursor_key_id="old",
    )

    _, first = _request(
        app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1},
    )
    cursor = first["data"]["next_cursor"]

    status, mismatch = _request(
        app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "OTHER", "limit": 1, "cursor": cursor},
    )
    assert status == 400
    assert "different query or filter set" in mismatch["error"]["message"]

    writer = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(writer)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                "R4",
                "PART-AUTH",
                "REV04",
                T0 + timedelta(hours=1),
                parent_revision_id="R3",
            ),
            event_id="LC-R4",
        )
    writer.close()

    fresh_app = build_read_only_lifecycle_http_app(
        database,
        cursor_signing_key=OLD_KEY,
        cursor_key_id="old",
    )
    status, stale = _request(
        fresh_app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1, "cursor": cursor},
    )
    assert status == 400
    assert "snapshot is stale" in stale["error"]["message"]


def test_checksum_only_mode_remains_backward_compatible(tmp_path) -> None:
    database = tmp_path / "legacy.db"
    _seed_database(database)
    app = build_read_only_lifecycle_http_app(database)

    status, health = _request(app, "/health")
    assert status == 200
    assert health["data"]["cursor_authentication"] == "checksum-only"
    assert "cursor_key_id" not in health["data"]

    status, first = _request(
        app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1},
    )
    cursor = first["data"]["next_cursor"]
    status, second = _request(
        app,
        "/v1/knowledge/revision-outcomes",
        {"part_id": "PART-AUTH", "limit": 1, "cursor": cursor},
    )
    assert status == 200
    assert second["data"]["items"][0]["revision_id"] == "R2"
