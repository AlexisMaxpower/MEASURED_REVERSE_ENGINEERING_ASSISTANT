from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import parse_qs

from .http_cursor import HttpCursorAuthenticator
from .knowledge_paging import LifecycleKnowledgeCursorError
from .read_only import (
    LifecycleReadOnlyError,
    LifecycleReadOnlyStaleError,
    SQLiteLifecycleReadOnlySession,
)


LIFECYCLE_HTTP_API_SCHEMA_VERSION = "mrea.lifecycle-http.v1"


class LifecycleHttpRequestError(ValueError):
    """Raised when a read-only HTTP request violates the local API contract."""


class LifecycleHttpNotFoundError(LifecycleHttpRequestError):
    """Raised when the requested local API route does not exist."""


class LifecycleHttpMethodNotAllowedError(LifecycleHttpRequestError):
    """Raised when a method other than GET is used."""


class LifecycleHttpResponse:
    __slots__ = ("status", "body", "headers")

    def __init__(
        self,
        *,
        status: int,
        body: bytes,
        headers: tuple[tuple[str, str], ...],
    ) -> None:
        self.status = status
        self.body = body
        self.headers = headers


_STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    503: "Service Unavailable",
}


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _json_response(
    *,
    status: int,
    payload: Mapping[str, Any],
    extra_headers: tuple[tuple[str, str], ...] = (),
) -> LifecycleHttpResponse:
    body = json.dumps(
        _jsonable(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    headers = (
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ) + extra_headers
    return LifecycleHttpResponse(status=status, body=body, headers=headers)


def _parse_query(raw_query: str) -> dict[str, list[str]]:
    try:
        return parse_qs(
            raw_query,
            keep_blank_values=True,
            strict_parsing=False,
            encoding="utf-8",
            errors="strict",
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise LifecycleHttpRequestError("invalid query string encoding") from exc


def _validate_query_keys(
    query: Mapping[str, list[str]],
    *,
    allowed: set[str],
) -> None:
    unexpected = sorted(set(query) - allowed)
    if unexpected:
        raise LifecycleHttpRequestError(
            "unexpected query parameter(s): " + ", ".join(unexpected)
        )


def _single_query_value(
    query: Mapping[str, list[str]],
    name: str,
    *,
    required: bool = False,
) -> Optional[str]:
    values = query.get(name)
    if values is None:
        if required:
            raise LifecycleHttpRequestError(f"missing required query parameter: {name}")
        return None
    if len(values) != 1:
        raise LifecycleHttpRequestError(f"query parameter must appear once: {name}")
    value = values[0]
    if value == "":
        if required:
            raise LifecycleHttpRequestError(f"query parameter must not be blank: {name}")
        return None
    return value


def _page_limit(query: Mapping[str, list[str]]) -> int:
    raw = _single_query_value(query, "limit")
    if raw is None:
        return 100
    try:
        return int(raw, 10)
    except ValueError as exc:
        raise LifecycleHttpRequestError("limit must be a base-10 integer") from exc


class ReadOnlyLifecycleHttpAPI:
    """Dependency-free WSGI adapter over the committed read-only lifecycle store.

    The adapter exposes GET-only JSON endpoints. Every successful data request opens a
    fresh SQLiteLifecycleReadOnlySession, so the existing read-only, schema and
    snapshot-consistency checks remain the authority for every response.

    If cursor_authenticator is configured, every paginated cursor crossing the HTTP
    boundary is HMAC-authenticated while the inner Pass-8 knowledge cursor continues
    to enforce query identity and snapshot binding.
    """

    def __init__(
        self,
        database: str | Path,
        *,
        cursor_authenticator: Optional[HttpCursorAuthenticator] = None,
    ) -> None:
        self.database = Path(database)
        self.cursor_authenticator = cursor_authenticator

    def __call__(
        self,
        environ: Mapping[str, Any],
        start_response: Callable[[str, list[tuple[str, str]]], Any],
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", ""))
        raw_query = str(environ.get("QUERY_STRING", ""))
        response = self.dispatch(method=method, path=path, raw_query=raw_query)
        reason = _STATUS_TEXT[response.status]
        start_response(
            f"{response.status} {reason}",
            list(response.headers),
        )
        return [response.body]

    def dispatch(
        self,
        *,
        method: str,
        path: str,
        raw_query: str = "",
    ) -> LifecycleHttpResponse:
        try:
            if method.upper() != "GET":
                raise LifecycleHttpMethodNotAllowedError("only GET is supported")
            query = _parse_query(raw_query)
            if path == "/health":
                _validate_query_keys(query, allowed=set())
                return self._with_session(lambda session: self._health(session))
            if path == "/v1/lifecycle/revisions":
                _validate_query_keys(query, allowed={"part_id"})
                part_id = _single_query_value(query, "part_id", required=True)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.queries.revision_history(part_id),
                    )
                )
            if path == "/v1/lifecycle/failures":
                _validate_query_keys(query, allowed={"revision_id", "instance_id"})
                revision_id = _single_query_value(query, "revision_id")
                instance_id = _single_query_value(query, "instance_id")
                if revision_id is None and instance_id is None:
                    raise LifecycleHttpRequestError(
                        "revision_id or instance_id is required"
                    )
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.queries.failure_history(
                            revision_id=revision_id,
                            instance_id=instance_id,
                        ),
                    )
                )
            if path == "/v1/lifecycle/equipment-occupancy":
                _validate_query_keys(query, allowed={"equipment_id", "position"})
                equipment_id = _single_query_value(
                    query, "equipment_id", required=True
                )
                position = _single_query_value(query, "position")
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.queries.equipment_occupancy(
                            equipment_id=equipment_id,
                            position=position,
                        ),
                    )
                )
            if path == "/v1/lifecycle/physical-timeline":
                _validate_query_keys(query, allowed={"instance_id"})
                instance_id = _single_query_value(query, "instance_id", required=True)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.queries.physical_timeline(instance_id),
                    )
                )
            if path == "/v1/knowledge/revision-lineage":
                _validate_query_keys(query, allowed={"part_id"})
                part_id = _single_query_value(query, "part_id", required=True)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.knowledge.revision_lineage(part_id),
                    )
                )
            if path == "/v1/knowledge/revision-comparison":
                _validate_query_keys(
                    query,
                    allowed={"left_revision_id", "right_revision_id"},
                )
                left_revision_id = _single_query_value(
                    query, "left_revision_id", required=True
                )
                right_revision_id = _single_query_value(
                    query, "right_revision_id", required=True
                )
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.knowledge.compare_revisions(
                            left_revision_id,
                            right_revision_id,
                        ),
                    )
                )
            if path == "/v1/knowledge/revision-comparison-details":
                _validate_query_keys(
                    query,
                    allowed={"left_revision_id", "right_revision_id"},
                )
                left_revision_id = _single_query_value(
                    query, "left_revision_id", required=True
                )
                right_revision_id = _single_query_value(
                    query, "right_revision_id", required=True
                )
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.knowledge.compare_revision_details(
                            left_revision_id,
                            right_revision_id,
                        ),
                    )
                )
            if path == "/v1/knowledge/revision-outcomes":
                _validate_query_keys(query, allowed={"part_id", "limit", "cursor"})
                part_id = _single_query_value(query, "part_id", required=True)
                limit = _page_limit(query)
                cursor = self._incoming_cursor(query)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        self._externalize_page(
                            session.knowledge.revision_outcomes_page(
                                part_id,
                                limit=limit,
                                cursor=cursor,
                            )
                        ),
                    )
                )
            if path == "/v1/knowledge/equipment-history":
                _validate_query_keys(
                    query,
                    allowed={
                        "equipment_id",
                        "position",
                        "event_type",
                        "revision_id",
                        "instance_id",
                        "limit",
                        "cursor",
                    },
                )
                equipment_id = _single_query_value(
                    query, "equipment_id", required=True
                )
                cursor = self._incoming_cursor(query)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        self._externalize_page(
                            session.knowledge.equipment_position_history_page(
                                equipment_id=equipment_id,
                                position=_single_query_value(query, "position"),
                                event_type=_single_query_value(query, "event_type"),
                                revision_id=_single_query_value(query, "revision_id"),
                                instance_id=_single_query_value(query, "instance_id"),
                                limit=_page_limit(query),
                                cursor=cursor,
                            )
                        ),
                    )
                )
            if path == "/v1/knowledge/failure-patterns":
                _validate_query_keys(
                    query,
                    allowed={"part_id", "revision_id", "limit", "cursor"},
                )
                cursor = self._incoming_cursor(query)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        self._externalize_page(
                            session.knowledge.failure_patterns_page(
                                part_id=_single_query_value(query, "part_id"),
                                revision_id=_single_query_value(query, "revision_id"),
                                limit=_page_limit(query),
                                cursor=cursor,
                            )
                        ),
                    )
                )
            if path == "/v1/knowledge/replacement-chain":
                _validate_query_keys(query, allowed={"instance_id"})
                instance_id = _single_query_value(query, "instance_id", required=True)
                return self._with_session(
                    lambda session: self._success(
                        session,
                        session.knowledge.replacement_chain(instance_id),
                    )
                )
            raise LifecycleHttpNotFoundError(f"route not found: {path}")
        except LifecycleHttpMethodNotAllowedError as exc:
            return self._error(
                status=405,
                code="method_not_allowed",
                message=str(exc),
                extra_headers=(("Allow", "GET"),),
            )
        except LifecycleHttpNotFoundError as exc:
            return self._error(status=404, code="route_not_found", message=str(exc))
        except (LifecycleHttpRequestError, LifecycleKnowledgeCursorError, ValueError) as exc:
            return self._error(status=400, code="invalid_request", message=str(exc))
        except LifecycleReadOnlyStaleError as exc:
            return self._error(
                status=409,
                code="read_model_stale",
                message=str(exc),
            )
        except LifecycleReadOnlyError as exc:
            return self._error(
                status=503,
                code="read_model_unavailable",
                message=str(exc),
            )

    def _incoming_cursor(self, query: Mapping[str, list[str]]) -> Optional[str]:
        cursor = _single_query_value(query, "cursor")
        if cursor is None or self.cursor_authenticator is None:
            return cursor
        return self.cursor_authenticator.verify(cursor)

    def _externalize_page(self, page: Any) -> Mapping[str, Any]:
        next_cursor = page.next_cursor
        if next_cursor is not None and self.cursor_authenticator is not None:
            next_cursor = self.cursor_authenticator.sign(next_cursor)
        return {
            "items": page.items,
            "next_cursor": next_cursor,
            "snapshot_version": page.snapshot_version,
        }

    def _with_session(
        self,
        handler: Callable[[SQLiteLifecycleReadOnlySession], LifecycleHttpResponse],
    ) -> LifecycleHttpResponse:
        with SQLiteLifecycleReadOnlySession(self.database) as session:
            return handler(session)

    @staticmethod
    def _success(
        session: SQLiteLifecycleReadOnlySession,
        data: Any,
    ) -> LifecycleHttpResponse:
        return _json_response(
            status=200,
            payload={
                "schema_version": LIFECYCLE_HTTP_API_SCHEMA_VERSION,
                "snapshot_version": session.snapshot_version,
                "data": data,
            },
        )

    def _health(self, session: SQLiteLifecycleReadOnlySession) -> LifecycleHttpResponse:
        data: dict[str, Any] = {
            "status": "ok",
            "read_only": True,
            "read_model_version": session.read_model_version,
            "relational_schema_version": session.relational_schema_version,
            "cursor_authentication": (
                "hmac-sha256"
                if self.cursor_authenticator is not None
                else "checksum-only"
            ),
        }
        if self.cursor_authenticator is not None:
            data["cursor_key_id"] = self.cursor_authenticator.key_id
        return _json_response(
            status=200,
            payload={
                "schema_version": LIFECYCLE_HTTP_API_SCHEMA_VERSION,
                "snapshot_version": session.snapshot_version,
                "data": data,
            },
        )

    @staticmethod
    def _error(
        *,
        status: int,
        code: str,
        message: str,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> LifecycleHttpResponse:
        return _json_response(
            status=status,
            payload={
                "schema_version": LIFECYCLE_HTTP_API_SCHEMA_VERSION,
                "error": {"code": code, "message": message},
            },
            extra_headers=extra_headers,
        )


def build_read_only_lifecycle_http_app(
    database: str | Path,
    *,
    cursor_signing_key: Optional[bytes] = None,
    cursor_key_id: str = "default",
    cursor_verification_keys: Optional[Mapping[str, bytes]] = None,
) -> ReadOnlyLifecycleHttpAPI:
    if cursor_signing_key is None:
        if cursor_verification_keys:
            raise ValueError(
                "cursor_verification_keys require cursor_signing_key"
            )
        authenticator = None
    else:
        authenticator = HttpCursorAuthenticator(
            cursor_signing_key,
            key_id=cursor_key_id,
            verification_keys=cursor_verification_keys,
        )
    return ReadOnlyLifecycleHttpAPI(
        database,
        cursor_authenticator=authenticator,
    )
