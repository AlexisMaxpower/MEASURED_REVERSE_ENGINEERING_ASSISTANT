from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
from typing import Generic, Mapping, Optional, Sequence, TypeVar


KNOWLEDGE_CURSOR_FORMAT_VERSION = "mrea.knowledge-cursor.v1"
DEFAULT_KNOWLEDGE_PAGE_LIMIT = 100
MAX_KNOWLEDGE_PAGE_LIMIT = 500


class LifecycleKnowledgeCursorError(ValueError):
    """Raised when a knowledge cursor cannot be safely continued."""


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class KnowledgePage(Generic[T]):
    items: tuple[T, ...]
    next_cursor: Optional[str]
    snapshot_version: int


@dataclass(frozen=True, slots=True)
class KnowledgeCursorState:
    offset: int
    snapshot_version: int


def validate_page_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise LifecycleKnowledgeCursorError("knowledge page limit must be an integer")
    if limit < 1 or limit > MAX_KNOWLEDGE_PAGE_LIMIT:
        raise LifecycleKnowledgeCursorError(
            "knowledge page limit must be between 1 and "
            f"{MAX_KNOWLEDGE_PAGE_LIMIT}"
        )
    return limit


def query_fingerprint(name: str, filters: Mapping[str, object]) -> str:
    canonical = json.dumps(
        {"name": name, "filters": dict(filters)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor encoding") from exc


def encode_knowledge_cursor(
    *,
    query_fingerprint_value: str,
    snapshot_version: int,
    offset: int,
) -> str:
    if snapshot_version < 0:
        raise LifecycleKnowledgeCursorError("snapshot version must be non-negative")
    if offset < 0:
        raise LifecycleKnowledgeCursorError("cursor offset must be non-negative")

    payload = {
        "v": KNOWLEDGE_CURSOR_FORMAT_VERSION,
        "q": query_fingerprint_value,
        "s": snapshot_version,
        "o": offset,
    }
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    envelope = {
        "p": _encode_bytes(payload_bytes),
        "c": hashlib.sha256(payload_bytes).hexdigest(),
    }
    return _encode_bytes(
        json.dumps(
            envelope,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def decode_knowledge_cursor(
    cursor: str,
    *,
    expected_query_fingerprint: str,
    expected_snapshot_version: int,
) -> KnowledgeCursorState:
    if not isinstance(cursor, str) or not cursor:
        raise LifecycleKnowledgeCursorError("knowledge cursor must be a non-empty string")

    try:
        envelope = json.loads(_decode_bytes(cursor).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor envelope") from exc
    if not isinstance(envelope, dict) or set(envelope) != {"p", "c"}:
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor envelope")
    encoded_payload = envelope["p"]
    checksum = envelope["c"]
    if not isinstance(encoded_payload, str) or not isinstance(checksum, str):
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor envelope")

    payload_bytes = _decode_bytes(encoded_payload)
    if hashlib.sha256(payload_bytes).hexdigest() != checksum:
        raise LifecycleKnowledgeCursorError("knowledge cursor checksum mismatch")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor payload") from exc
    if not isinstance(payload, dict) or set(payload) != {"v", "q", "s", "o"}:
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor payload")
    if payload["v"] != KNOWLEDGE_CURSOR_FORMAT_VERSION:
        raise LifecycleKnowledgeCursorError(
            f"unsupported knowledge cursor format: {payload['v']}"
        )
    if payload["q"] != expected_query_fingerprint:
        raise LifecycleKnowledgeCursorError(
            "knowledge cursor belongs to a different query or filter set"
        )

    snapshot_version = payload["s"]
    offset = payload["o"]
    if (
        isinstance(snapshot_version, bool)
        or not isinstance(snapshot_version, int)
        or snapshot_version < 0
        or isinstance(offset, bool)
        or not isinstance(offset, int)
        or offset < 0
    ):
        raise LifecycleKnowledgeCursorError("invalid knowledge cursor numeric state")
    if snapshot_version != expected_snapshot_version:
        raise LifecycleKnowledgeCursorError(
            "knowledge cursor snapshot is stale: "
            f"cursor={snapshot_version}, current={expected_snapshot_version}"
        )
    return KnowledgeCursorState(
        offset=offset,
        snapshot_version=snapshot_version,
    )


def page_from_rows(
    rows: Sequence[T],
    *,
    limit: int,
    offset: int,
    query_fingerprint_value: str,
    snapshot_version: int,
) -> KnowledgePage[T]:
    page_limit = validate_page_limit(limit)
    visible = tuple(rows[:page_limit])
    has_more = len(rows) > page_limit
    next_cursor = None
    if has_more:
        next_cursor = encode_knowledge_cursor(
            query_fingerprint_value=query_fingerprint_value,
            snapshot_version=snapshot_version,
            offset=offset + page_limit,
        )
    return KnowledgePage(
        items=visible,
        next_cursor=next_cursor,
        snapshot_version=snapshot_version,
    )
