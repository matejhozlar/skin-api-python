from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from createrington_skin_api import (
    DEFAULT_BASE_URL,
    KNOWN_POSES,
    SkinApiClient,
    SkinApiError,
    random_pose,
)
from createrington_skin_api._core import _RETRY_AFTER_MAX_MS, retry_delay_seconds

PNG_BYTES = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00])

Handler = Callable[[httpx.Request], httpx.Response]


def png_handler(captured: list[httpx.Request]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, content=PNG_BYTES, headers={"content-type": "image/png"}
        )

    return handler


def make_client(handler: Handler, **kwargs: object) -> SkinApiClient:
    return SkinApiClient(
        api_key="test-key",
        base_url="http://skin.test",
        transport=httpx.MockTransport(handler),
        **kwargs,  # type: ignore[arg-type]
    )


def test_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKIN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="api_key is required"):
        SkinApiClient()


def test_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIN_API_KEY", "env-key")
    captured: list[httpx.Request] = []
    client = SkinApiClient(
        base_url="http://skin.test",
        transport=httpx.MockTransport(png_handler(captured)),
    )
    client.render("wave", uuid="abc")
    assert captured[0].headers["authorization"] == "Bearer env-key"


def test_default_base_url_is_createrington() -> None:
    captured: list[httpx.Request] = []
    client = SkinApiClient(
        api_key="test-key",
        transport=httpx.MockTransport(png_handler(captured)),
    )
    client.render("wave", uuid="abc")
    assert str(captured[0].url).startswith(DEFAULT_BASE_URL)
    assert DEFAULT_BASE_URL == "https://api.createrington.com"


def test_sends_bearer_auth_and_get_query_for_uuid() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    out = client.render("wave", uuid="uuid-1", slim=True, width=200, height=300)
    request = captured[0]
    assert out == PNG_BYTES
    assert request.method == "GET"
    assert request.url.path == "/v1/render"
    assert dict(request.url.params) == {
        "pose": "wave",
        "slim": "true",
        "width": "200",
        "height": "300",
        "uuid": "uuid-1",
    }
    assert request.headers["authorization"] == "Bearer test-key"
    assert request.content == b""


def test_sends_get_query_for_username() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    out = client.render("wave", username="Steve")
    request = captured[0]
    assert out == PNG_BYTES
    assert request.method == "GET"
    assert request.url.path == "/v1/render"
    assert dict(request.url.params) == {"pose": "wave", "username": "Steve"}
    assert request.content == b""


def test_outline_true_sends_outline_param() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", uuid="uuid-1", outline=True)
    assert dict(captured[0].url.params) == {
        "pose": "wave",
        "outline": "true",
        "uuid": "uuid-1",
    }


def test_outline_omitted_when_false() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", uuid="uuid-1", outline=False)
    assert "outline" not in dict(captured[0].url.params)


def test_outline_omitted_by_default() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", uuid="uuid-1")
    assert "outline" not in dict(captured[0].url.params)


def test_sets_user_agent() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", uuid="x")
    assert captured[0].headers["user-agent"] == "createrington-skin-api"


def test_png_source_uses_multipart() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", png=PNG_BYTES)
    request = captured[0]
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b'name="skin"' in request.content
    assert PNG_BYTES in request.content


def test_skin_url_maps_to_camel_case_field() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", skin_url="https://example.com/skin.png")
    request = captured[0]
    assert request.method == "POST"
    assert json.loads(request.content) == {"skinUrl": "https://example.com/skin.png"}


def test_skin_base64_maps_to_camel_case_field() -> None:
    captured: list[httpx.Request] = []
    client = make_client(png_handler(captured))
    client.render("wave", skin_base64="AAAA")
    request = captured[0]
    assert request.method == "POST"
    assert json.loads(request.content) == {"skinBase64": "AAAA"}


def test_no_source_raises_value_error() -> None:
    client = make_client(png_handler([]))
    with pytest.raises(ValueError, match="requires exactly one skin source"):
        client.render("wave")


def test_multiple_sources_raise_value_error() -> None:
    client = make_client(png_handler([]))
    with pytest.raises(ValueError, match="exactly one skin source"):
        client.render("wave", uuid="x", username="y")


def test_normalizes_upper_snake_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404, json={"error": {"code": "NOT_FOUND", "message": "Pose missing"}}
        )

    client = make_client(handler, retries=0)
    with pytest.raises(SkinApiError) as info:
        client.render("wave", uuid="x")
    err = info.value
    assert err.code == "not_found"
    assert err.status == 404
    assert str(err) == "Pose missing"


def test_falls_back_to_status_code_when_body_code_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": "WAT", "message": "huh"}})

    client = make_client(handler, retries=0)
    with pytest.raises(SkinApiError) as info:
        client.render("wave", uuid="x")
    assert info.value.code == "bad_request"
    assert info.value.status == 400


def test_retries_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                json={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "slow down",
                        "retryAfterMs": 5,
                    }
                },
            )
        return httpx.Response(
            200, content=PNG_BYTES, headers={"content-type": "image/png"}
        )

    client = make_client(handler, retries=1)
    out = client.render("wave", uuid="x")
    assert out == PNG_BYTES
    assert calls["n"] == 2


def test_does_not_retry_when_retries_zero() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            429,
            json={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "slow down",
                    "retryAfterMs": 5,
                }
            },
        )

    client = make_client(handler, retries=0)
    with pytest.raises(SkinApiError) as info:
        client.render("wave", uuid="x")
    assert info.value.code == "rate_limited"
    assert info.value.status == 429
    assert info.value.retry_after_ms == 5
    assert calls["n"] == 1


def test_network_error_maps_to_network_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = make_client(handler, retries=0)
    with pytest.raises(SkinApiError) as info:
        client.render("wave", uuid="x")
    assert info.value.code == "network_error"
    assert info.value.status == 0


def test_timeout_maps_to_timeout_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client = make_client(handler, retries=0)
    with pytest.raises(SkinApiError) as info:
        client.render("wave", uuid="x")
    assert info.value.code == "timeout"
    assert info.value.status == 0


def test_context_manager_closes_client() -> None:
    captured: list[httpx.Request] = []
    with make_client(png_handler(captured)) as client:
        client.render("wave", uuid="x")
    assert client._client.is_closed


def test_known_poses_populated() -> None:
    assert isinstance(KNOWN_POSES, tuple)
    assert len(KNOWN_POSES) > 0
    assert "wave" in KNOWN_POSES


def test_random_pose_is_always_known() -> None:
    for _ in range(50):
        assert random_pose() in KNOWN_POSES


def test_retry_delay_honors_positive_retry_after() -> None:
    assert retry_delay_seconds(429, {"error": {"retryAfterMs": 5}}, 0) == 0.005


def test_retry_delay_caps_excessive_retry_after() -> None:
    one_day = {"error": {"retryAfterMs": 24 * 60 * 60 * 1000}}
    assert retry_delay_seconds(429, one_day, 0) == _RETRY_AFTER_MAX_MS / 1000.0


def test_retry_delay_falls_back_to_backoff_for_non_positive() -> None:
    # A negative value would crash time.sleep(); zero would retry instantly.
    # Both must fall through to the normal backoff window instead.
    for value in (-100, 0):
        delay = retry_delay_seconds(429, {"error": {"retryAfterMs": value}}, 0)
        assert 0.2 <= delay < 0.25


def test_retry_delay_uses_backoff_for_non_429() -> None:
    delay = retry_delay_seconds(503, {"error": {"retryAfterMs": 5}}, 0)
    assert 0.2 <= delay < 0.25
