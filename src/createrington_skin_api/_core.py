from __future__ import annotations

import random
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.createrington.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 2
DEFAULT_USER_AGENT = "createrington-skin-api"
API_KEY_ENV = "SKIN_API_KEY"

_BACKOFF_BASE_MS = 200
_BACKOFF_MAX_MS = 5_000
_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})

# Bounds how long a server-provided retryAfterMs may pause a retry, so a
# misbehaving server cannot make the client hang. The true value is still
# surfaced on SkinApiError.retry_after_ms.
_RETRY_AFTER_MAX_MS = 60_000

# render() keyword name -> JSON body field name. png is multipart, not JSON.
_JSON_SOURCE_FIELDS: dict[str, str] = {
    "uuid": "uuid",
    "username": "username",
    "skin_url": "skinUrl",
    "skin_base64": "skinBase64",
}


@dataclass(frozen=True)
class PreparedRender:
    url: str
    params: dict[str, str]
    json: dict[str, str] | None = None
    files: dict[str, tuple[str, bytes, str]] | None = None


def _select_source(
    *,
    uuid: str | None,
    username: str | None,
    skin_url: str | None,
    skin_base64: str | None,
    png: bytes | bytearray | memoryview | None,
) -> str:
    given = [
        name
        for name, value in (
            ("uuid", uuid),
            ("username", username),
            ("skin_url", skin_url),
            ("skin_base64", skin_base64),
            ("png", png),
        )
        if value is not None
    ]

    if not given:
        raise ValueError(
            "render() requires exactly one skin source: pass one of "
            "uuid, username, skin_url, skin_base64, or png"
        )
    if len(given) > 1:
        raise ValueError(
            "render() accepts exactly one skin source, but several were given: "
            + ", ".join(given)
        )
    return given[0]


def prepare_render(
    base_url: str,
    pose: str,
    *,
    uuid: str | None,
    username: str | None,
    skin_url: str | None,
    skin_base64: str | None,
    png: bytes | bytearray | memoryview | None,
    slim: bool | None,
    outline: bool | None,
    width: int | None,
    height: int | None,
) -> PreparedRender:
    name = _select_source(
        uuid=uuid,
        username=username,
        skin_url=skin_url,
        skin_base64=skin_base64,
        png=png,
    )

    params: dict[str, str] = {"pose": pose}
    if slim is not None:
        params["slim"] = "true" if slim else "false"
    # outline defaults OFF server-side; omit when falsy so the render cache key
    # for non-outline calls is unchanged.
    if outline:
        params["outline"] = "true"
    if width is not None:
        params["width"] = str(width)
    if height is not None:
        params["height"] = str(height)

    url = f"{base_url}/v1/render"

    if name == "png":
        assert png is not None
        return PreparedRender(
            url=url,
            params=params,
            files={"skin": ("skin.png", bytes(png), "image/png")},
        )

    value = {
        "uuid": uuid,
        "username": username,
        "skin_url": skin_url,
        "skin_base64": skin_base64,
    }[name]
    assert value is not None
    return PreparedRender(
        url=url,
        params=params,
        json={_JSON_SOURCE_FIELDS[name]: value},
    )


def is_retryable_status(status: int) -> bool:
    return status in _RETRYABLE_STATUSES


def _backoff_seconds(attempt: int) -> float:
    capped = min(_BACKOFF_BASE_MS * (1 << attempt), _BACKOFF_MAX_MS)
    jitter = capped * 0.25 * random.random()
    return (capped + jitter) / 1000.0


def retry_delay_seconds(status: int, body: object, attempt: int) -> float:
    if status == 429 and isinstance(body, dict):
        info = body.get("error")
        if isinstance(info, dict):
            retry_after = info.get("retryAfterMs")
            if (
                isinstance(retry_after, (int, float))
                and not isinstance(retry_after, bool)
                and retry_after > 0
            ):
                capped = min(float(retry_after), float(_RETRY_AFTER_MAX_MS))
                return capped / 1000.0
    return _backoff_seconds(attempt)
