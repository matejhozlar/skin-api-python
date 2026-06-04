from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from createrington_skin_api import AsyncSkinApiClient, SkinApiError

PNG_BYTES = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00])

Handler = Callable[[httpx.Request], httpx.Response]


def png_handler(captured: list[httpx.Request]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, content=PNG_BYTES, headers={"content-type": "image/png"}
        )

    return handler


def make_client(handler: Handler, **kwargs: object) -> AsyncSkinApiClient:
    return AsyncSkinApiClient(
        api_key="test-key",
        base_url="http://skin.test",
        transport=httpx.MockTransport(handler),
        **kwargs,  # type: ignore[arg-type]
    )


async def test_sends_bearer_auth_and_json_body_for_uuid() -> None:
    captured: list[httpx.Request] = []
    async with make_client(png_handler(captured)) as client:
        out = await client.render("wave", uuid="uuid-1", slim=False, width=128)
    request = captured[0]
    assert out == PNG_BYTES
    assert request.method == "POST"
    assert request.url.path == "/v1/render"
    assert dict(request.url.params) == {
        "pose": "wave",
        "slim": "false",
        "width": "128",
    }
    assert request.headers["authorization"] == "Bearer test-key"
    assert json.loads(request.content) == {"uuid": "uuid-1"}


async def test_outline_true_sends_outline_param() -> None:
    captured: list[httpx.Request] = []
    async with make_client(png_handler(captured)) as client:
        await client.render("wave", uuid="uuid-1", outline=True)
    assert dict(captured[0].url.params) == {"pose": "wave", "outline": "true"}


async def test_outline_omitted_by_default() -> None:
    captured: list[httpx.Request] = []
    async with make_client(png_handler(captured)) as client:
        await client.render("wave", uuid="uuid-1")
    assert "outline" not in dict(captured[0].url.params)


async def test_png_source_uses_multipart() -> None:
    captured: list[httpx.Request] = []
    async with make_client(png_handler(captured)) as client:
        await client.render("wave", png=PNG_BYTES)
    request = captured[0]
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert PNG_BYTES in request.content


async def test_no_source_raises_value_error() -> None:
    async with make_client(png_handler([])) as client:
        with pytest.raises(ValueError, match="requires exactly one skin source"):
            await client.render("wave")


async def test_normalizes_upper_snake_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404, json={"error": {"code": "NOT_FOUND", "message": "Pose missing"}}
        )

    async with make_client(handler, retries=0) as client:
        with pytest.raises(SkinApiError) as info:
            await client.render("wave", uuid="x")
    assert info.value.code == "not_found"
    assert info.value.status == 404
    assert str(info.value) == "Pose missing"


async def test_retries_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                json={"error": {"code": "RATE_LIMITED", "retryAfterMs": 5}},
            )
        return httpx.Response(
            200, content=PNG_BYTES, headers={"content-type": "image/png"}
        )

    async with make_client(handler, retries=1) as client:
        out = await client.render("wave", uuid="x")
    assert out == PNG_BYTES
    assert calls["n"] == 2


async def test_does_not_retry_when_retries_zero() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"error": {"code": "RATE_LIMITED", "retryAfterMs": 5}}
        )

    async with make_client(handler, retries=0) as client:
        with pytest.raises(SkinApiError) as info:
            await client.render("wave", uuid="x")
    assert info.value.code == "rate_limited"
    assert info.value.retry_after_ms == 5


async def test_network_error_maps_to_network_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    async with make_client(handler, retries=0) as client:
        with pytest.raises(SkinApiError) as info:
            await client.render("wave", uuid="x")
    assert info.value.code == "network_error"


async def test_timeout_maps_to_timeout_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async with make_client(handler, retries=0) as client:
        with pytest.raises(SkinApiError) as info:
            await client.render("wave", uuid="x")
    assert info.value.code == "timeout"
