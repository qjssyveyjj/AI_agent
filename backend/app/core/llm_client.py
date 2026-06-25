from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return _client


async def chat_once(messages: list[dict], tools: list[dict] | None = None):
    """非流式：用于 Agent 循环中判断是否需要工具调用。返回 message 对象。"""
    kwargs: dict = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    resp = await get_client().chat.completions.create(**kwargs)
    return resp.choices[0].message


async def chat_stream(messages: list[dict]) -> AsyncIterator[str]:
    """流式：用于生成最终面向用户的自然语言答复。逐段返回文本增量。"""
    stream = await get_client().chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
