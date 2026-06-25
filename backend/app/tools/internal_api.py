from typing import Any

import httpx

from app.config import settings

_client: httpx.AsyncClient | None = None


def get_internal_client() -> httpx.AsyncClient:
    """对内部 dev-api 的统一异步客户端，认证集中在此处理。"""
    global _client
    if _client is None:
        headers = {}
        if settings.internal_api_token:
            headers["Authorization"] = f"Bearer {settings.internal_api_token}"
        _client = httpx.AsyncClient(
            base_url=settings.internal_api_base,
            headers=headers,
            timeout=settings.internal_api_timeout,
        )
    return _client


async def call_internal_api(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """调用内部 API 并返回 JSON。异常被规整为结构化错误，避免中断 Agent 循环。"""
    client = get_internal_client()
    try:
        resp = await client.request(method.upper(), path, params=params, json=json)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}
    except httpx.HTTPStatusError as e:
        return {"error": "http_status", "status": e.response.status_code, "detail": e.response.text[:500]}
    except httpx.HTTPError as e:
        return {"error": "request_failed", "detail": str(e)}


async def close_internal_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
