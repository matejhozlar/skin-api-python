from __future__ import annotations

import httpx


def safe_json(response: httpx.Response) -> object:
    """Parse a response body as JSON, returning None when it is not JSON."""
    try:
        return response.json()
    except ValueError:
        return None


def default_headers(api_key: str, user_agent: str) -> dict[str, str]:
    return {
        "authorization": f"Bearer {api_key}",
        "user-agent": user_agent,
    }


def resolve_api_key(api_key: str | None, env_value: str | None) -> str:
    key = api_key if api_key is not None else env_value
    if not key:
        raise ValueError(
            "api_key is required: pass api_key=... or set the "
            "SKIN_API_KEY environment variable"
        )
    return key
