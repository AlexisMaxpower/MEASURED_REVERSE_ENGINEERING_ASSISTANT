from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Mapping, Optional


HTTP_CURSOR_FORMAT_VERSION = "mrea.http-cursor.v1"
MIN_HTTP_CURSOR_KEY_BYTES = 32


class LifecycleHttpCursorError(ValueError):
    """Raised when an authenticated HTTP cursor cannot be trusted."""


def _encode_bytes(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_bytes(token: str) -> bytes:
    padding = "=" * ((4 - len(token) % 4) % 4)
    try:
        return base64.b64decode(
            token + padding,
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as exc:
        raise LifecycleHttpCursorError("invalid HTTP cursor encoding") from exc


def _validate_key(key: bytes, *, name: str) -> bytes:
    if not isinstance(key, bytes):
        raise LifecycleHttpCursorError(f"{name} must be bytes")
    if len(key) < MIN_HTTP_CURSOR_KEY_BYTES:
        raise LifecycleHttpCursorError(
            f"{name} must be at least {MIN_HTTP_CURSOR_KEY_BYTES} bytes"
        )
    return key


def _validate_key_id(key_id: str) -> str:
    if not isinstance(key_id, str) or not key_id or len(key_id) > 128:
        raise LifecycleHttpCursorError(
            "HTTP cursor key_id must be a non-empty string up to 128 characters"
        )
    return key_id


class HttpCursorAuthenticator:
    """HMAC-SHA256 wrapper for an existing snapshot-bound knowledge cursor.

    The inner knowledge cursor remains authoritative for query identity, offset and
    snapshot binding. This wrapper adds authentication for transport across an
    untrusted boundary and supports verification of previous keys during rotation.
    """

    def __init__(
        self,
        signing_key: bytes,
        *,
        key_id: str = "default",
        verification_keys: Optional[Mapping[str, bytes]] = None,
    ) -> None:
        active_key_id = _validate_key_id(key_id)
        active_key = _validate_key(signing_key, name="HTTP cursor signing key")

        keys: dict[str, bytes] = {}
        if verification_keys is not None:
            for candidate_id, candidate_key in verification_keys.items():
                normalized_id = _validate_key_id(candidate_id)
                keys[normalized_id] = _validate_key(
                    candidate_key,
                    name=f"HTTP cursor verification key {normalized_id!r}",
                )

        existing = keys.get(active_key_id)
        if existing is not None and not hmac.compare_digest(existing, active_key):
            raise LifecycleHttpCursorError(
                "active HTTP cursor key_id conflicts with verification key"
            )
        keys[active_key_id] = active_key

        self._key_id = active_key_id
        self._signing_key = active_key
        self._verification_keys = keys

    @property
    def key_id(self) -> str:
        return self._key_id

    def sign(self, knowledge_cursor: str) -> str:
        if not isinstance(knowledge_cursor, str) or not knowledge_cursor:
            raise LifecycleHttpCursorError(
                "knowledge cursor must be a non-empty string"
            )
        payload = {
            "v": HTTP_CURSOR_FORMAT_VERSION,
            "kid": self._key_id,
            "c": knowledge_cursor,
        }
        payload_bytes = self._canonical_payload(payload)
        envelope = {
            **payload,
            "mac": hmac.new(
                self._signing_key,
                payload_bytes,
                hashlib.sha256,
            ).hexdigest(),
        }
        return _encode_bytes(
            json.dumps(
                envelope,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )

    def verify(self, cursor: str) -> str:
        if not isinstance(cursor, str) or not cursor:
            raise LifecycleHttpCursorError(
                "HTTP cursor must be a non-empty string"
            )
        try:
            envelope = json.loads(_decode_bytes(cursor).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LifecycleHttpCursorError("invalid HTTP cursor envelope") from exc
        if not isinstance(envelope, dict) or set(envelope) != {
            "v",
            "kid",
            "c",
            "mac",
        }:
            raise LifecycleHttpCursorError("invalid HTTP cursor envelope")
        if envelope["v"] != HTTP_CURSOR_FORMAT_VERSION:
            raise LifecycleHttpCursorError(
                f"unsupported HTTP cursor format: {envelope['v']}"
            )

        key_id = envelope["kid"]
        knowledge_cursor = envelope["c"]
        supplied_mac = envelope["mac"]
        if (
            not isinstance(key_id, str)
            or not isinstance(knowledge_cursor, str)
            or not knowledge_cursor
            or not isinstance(supplied_mac, str)
        ):
            raise LifecycleHttpCursorError("invalid HTTP cursor envelope")

        key = self._verification_keys.get(key_id)
        if key is None:
            raise LifecycleHttpCursorError("unknown HTTP cursor key_id")

        payload = {
            "v": envelope["v"],
            "kid": key_id,
            "c": knowledge_cursor,
        }
        expected_mac = hmac.new(
            key,
            self._canonical_payload(payload),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(supplied_mac, expected_mac):
            raise LifecycleHttpCursorError("HTTP cursor authentication failed")
        return knowledge_cursor

    @staticmethod
    def _canonical_payload(payload: Mapping[str, str]) -> bytes:
        return json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
