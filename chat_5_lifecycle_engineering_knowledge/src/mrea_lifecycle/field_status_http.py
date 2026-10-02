from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from .engineering_knowledge import LifecycleKnowledgeIntegrityError
from .field_status import get_physical_field_status
from .http_api import (
    LifecycleHttpMethodNotAllowedError,
    LifecycleHttpRequestError,
    LifecycleHttpResponse,
    ReadOnlyLifecycleHttpAPI as _BaseReadOnlyLifecycleHttpAPI,
    _parse_query,
    _single_query_value,
    _validate_query_keys,
    build_read_only_lifecycle_http_app as _build_base_http_app,
)
from .read_only import LifecycleReadOnlyError, LifecycleReadOnlyStaleError


PHYSICAL_FIELD_STATUS_ROUTE = "/v1/lifecycle/physical-field-status"


class PhysicalFieldStatusLifecycleHttpAPI(_BaseReadOnlyLifecycleHttpAPI):
    """Additive GET-only transport for durable physical field status.

    All pre-existing routes are delegated to the accepted base adapter unchanged.
    The new route projects one committed physical timeline through the same guarded
    read-only session used by the rest of Chat 5. Durable-history corruption is
    exposed as an explicit conflict instead of a plausible status or an unhandled
    server error.
    """

    def dispatch(
        self,
        *,
        method: str,
        path: str,
        raw_query: str = "",
    ) -> LifecycleHttpResponse:
        if path != PHYSICAL_FIELD_STATUS_ROUTE:
            return super().dispatch(method=method, path=path, raw_query=raw_query)

        try:
            if method.upper() != "GET":
                raise LifecycleHttpMethodNotAllowedError("only GET is supported")

            query = _parse_query(raw_query)
            _validate_query_keys(query, allowed={"instance_id"})
            instance_id = _single_query_value(query, "instance_id", required=True)
            return self._with_session(
                lambda session: self._success(
                    session,
                    get_physical_field_status(session.queries, instance_id),
                )
            )
        except LifecycleHttpMethodNotAllowedError as exc:
            return self._error(
                status=405,
                code="method_not_allowed",
                message=str(exc),
                extra_headers=(("Allow", "GET"),),
            )
        except (LifecycleHttpRequestError, ValueError) as exc:
            return self._error(
                status=400,
                code="invalid_request",
                message=str(exc),
            )
        except (LifecycleKnowledgeIntegrityError, LifecycleReadOnlyStaleError) as exc:
            return self._error(
                status=409,
                code=(
                    "read_model_integrity_error"
                    if isinstance(exc, LifecycleKnowledgeIntegrityError)
                    else "read_model_stale"
                ),
                message=str(exc),
            )
        except LifecycleReadOnlyError as exc:
            return self._error(
                status=503,
                code="read_model_unavailable",
                message=str(exc),
            )


def build_read_only_lifecycle_http_app(
    database: str | Path,
    *,
    cursor_signing_key: Optional[bytes] = None,
    cursor_key_id: str = "default",
    cursor_verification_keys: Optional[Mapping[str, bytes]] = None,
) -> PhysicalFieldStatusLifecycleHttpAPI:
    """Build the accepted HTTP adapter plus the Pass-19 field-status route."""

    base = _build_base_http_app(
        database,
        cursor_signing_key=cursor_signing_key,
        cursor_key_id=cursor_key_id,
        cursor_verification_keys=cursor_verification_keys,
    )
    return PhysicalFieldStatusLifecycleHttpAPI(
        database,
        cursor_authenticator=base.cursor_authenticator,
    )
