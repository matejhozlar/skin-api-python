from __future__ import annotations

import asyncio
import os
from types import TracebackType

import httpx

from . import _http
from ._core import (
    API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    is_retryable_status,
    prepare_render,
    retry_delay_seconds,
)
from ._poses import KnownPose
from .errors import SkinApiError, error_from_response


class AsyncSkinApiClient:
    """Asynchronous client for the Createrington Skin API.

    Renders Minecraft player skins into named poses and returns PNG bytes.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        user_agent: str = DEFAULT_USER_AGENT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create a client.

        Args:
            api_key: API key. Falls back to the ``SKIN_API_KEY`` environment
                variable when None.
            base_url: API base URL. Default ``https://api.createrington.com``.
            timeout: Per-request timeout in seconds. Default ``30.0``.
            retries: Retries for 429/502/503/504 and network errors, with
                exponential backoff. Default ``2``.
            user_agent: ``User-Agent`` header value.
            transport: Optional httpx transport (mainly for testing).
        """
        key = _http.resolve_api_key(api_key, os.environ.get(API_KEY_ENV))
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retries = retries
        self._client = httpx.AsyncClient(
            timeout=timeout,
            transport=transport,
            headers=_http.default_headers(key, user_agent),
        )

    async def render(
        self,
        pose: KnownPose | str,
        *,
        uuid: str | None = None,
        username: str | None = None,
        skin_url: str | None = None,
        skin_base64: str | None = None,
        png: bytes | bytearray | memoryview | None = None,
        slim: bool | None = None,
        outline: bool = False,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes:
        """Render ``pose`` for the given skin source and return PNG bytes.

        Exactly one skin source must be supplied. Retries
        ``429``/``502``/``503``/``504`` and network errors per ``retries``,
        honouring a ``429`` ``retryAfterMs`` when present.

        Args:
            pose: The pose to render, e.g. ``"wave"``. See ``KNOWN_POSES``.
            uuid: Mojang UUID; the official skin is resolved server-side.
            username: Mojang username; the current skin is resolved server-side.
            skin_url: Public URL to a 64x64 PNG skin.
            skin_base64: Base64-encoded 64x64 PNG (data URL prefix optional).
            png: Raw 64x64 PNG bytes, sent as ``multipart/form-data``.
            slim: Force slim (Alex) arm geometry; defaults to the skin's metadata.
            outline: Draw an outline around the rendered skin. Defaults to off.
            width: Output width in pixels (default 400, clamped 64..2048).
            height: Output height in pixels (default 600, clamped 64..2048).

        Returns:
            The rendered PNG image bytes.

        Raises:
            ValueError: If not exactly one skin source is provided.
            SkinApiError: On a non-2xx response, network error, or timeout.
        """
        prepared = prepare_render(
            self._base_url,
            pose,
            uuid=uuid,
            username=username,
            skin_url=skin_url,
            skin_base64=skin_base64,
            png=png,
            slim=slim,
            outline=outline,
            width=width,
            height=height,
        )

        attempt = 0
        while True:
            try:
                response = await self._client.request(
                    "POST",
                    prepared.url,
                    params=prepared.params,
                    json=prepared.json,
                    files=prepared.files,
                )
            except httpx.TimeoutException as exc:
                if attempt < self._retries:
                    await asyncio.sleep(retry_delay_seconds(0, None, attempt))
                    attempt += 1
                    continue
                raise SkinApiError(
                    f"Request timed out after {self._timeout}s",
                    code="timeout",
                    status=0,
                ) from exc
            except httpx.TransportError as exc:
                if attempt < self._retries:
                    await asyncio.sleep(retry_delay_seconds(0, None, attempt))
                    attempt += 1
                    continue
                raise SkinApiError(
                    str(exc) or "Network error",
                    code="network_error",
                    status=0,
                ) from exc

            if response.is_success:
                return response.content

            status = response.status_code
            body = _http.safe_json(response)

            if is_retryable_status(status) and attempt < self._retries:
                await asyncio.sleep(retry_delay_seconds(status, body, attempt))
                attempt += 1
                continue

            raise error_from_response(status, body)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncSkinApiClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()
