from __future__ import annotations

from typing import Literal

SkinApiErrorCode = Literal[
    "bad_request",
    "unauthorized",
    "forbidden",
    "not_found",
    "conflict",
    "unsupported_media_type",
    "rate_limited",
    "internal",
    "render_failed",
    "upstream_unavailable",
    "timeout",
    "aborted",
    "network_error",
    "unknown",
]

_KNOWN_CODES: frozenset[str] = frozenset(
    [
        "bad_request",
        "unauthorized",
        "forbidden",
        "not_found",
        "conflict",
        "unsupported_media_type",
        "rate_limited",
        "internal",
        "render_failed",
        "upstream_unavailable",
        "timeout",
        "aborted",
        "network_error",
        "unknown",
    ]
)

_STATUS_TO_CODE: dict[int, SkinApiErrorCode] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    415: "unsupported_media_type",
    429: "rate_limited",
    500: "internal",
    502: "upstream_unavailable",
    503: "upstream_unavailable",
    504: "upstream_unavailable",
}


class SkinApiError(Exception):
    """Raised for every non-2xx response and for network/timeout failures."""

    code: SkinApiErrorCode
    status: int
    retry_after_ms: int | None

    def __init__(
        self,
        message: str,
        *,
        code: SkinApiErrorCode,
        status: int,
        retry_after_ms: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after_ms = retry_after_ms

    def __repr__(self) -> str:
        return (
            f"SkinApiError(code={self.code!r}, status={self.status}, "
            f"message={str(self)!r})"
        )


# The server emits codes in UPPER_SNAKE (NOT_FOUND, RATE_LIMITED). The public
# surface documents the lower_snake form, so lowercase and validate against the
# documented set; consumer checks like `err.code == "rate_limited"` then match.
def _normalize_server_code(raw: str) -> SkinApiErrorCode | None:
    lowered = raw.lower()
    if lowered in _KNOWN_CODES:
        return lowered  # type: ignore[return-value]
    return None


def error_from_response(status: int, body: object) -> SkinApiError:
    info = body.get("error") if isinstance(body, dict) else None

    message: str | None = None
    code: SkinApiErrorCode | None = None
    retry_after_ms: int | None = None

    if isinstance(info, dict):
        raw_message = info.get("message")
        if isinstance(raw_message, str):
            message = raw_message
        raw_code = info.get("code")
        if isinstance(raw_code, str):
            code = _normalize_server_code(raw_code)
        raw_retry = info.get("retryAfterMs")
        if isinstance(raw_retry, (int, float)) and not isinstance(raw_retry, bool):
            retry_after_ms = int(raw_retry)

    return SkinApiError(
        message or f"HTTP {status}",
        code=code or _STATUS_TO_CODE.get(status, "unknown"),
        status=status,
        retry_after_ms=retry_after_ms,
    )
