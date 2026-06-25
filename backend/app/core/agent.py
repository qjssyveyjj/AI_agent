import json
from collections.abc import AsyncIterator
from typing import Any

from app.config import settings
from app.core.llm_client import chat_once, chat_stream
from app.tools.registry import registry

SYSTEM_PROMPT = (
    "你是一个内网企业助手，可以查看用户上传的截图并调用内部系统工具来回答问题。"
    "当需要查询订单、物流、用户等内部数据时，请调用提供的工具；"
    "请优先从截图中提取关键信息（如订单号、错误提示）。"
    "最终回答使用简洁、专业的中文。"
)


def build_user_message(text: str, image_data_urls: list[str] | None) -> dict:
    """构造多模态用户消息体。无图片时退化为纯文本。"""
    if not image_data_urls:
        return {"role": "user", "content": text}

    content: list[dict[str, Any]] = []
    if text:
        content.append({"type": "text", "text": text})
    for url in image_data_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return {"role": "user", "content": content}


def _assistant_tool_call_message(msg: Any) -> dict:
    return {
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ],
    }


async def run_agent(messages: list[dict]) -> AsyncIterator[dict]:
    """
    Agent 工具调用循环。
    产出事件流（供 SSE）：
      {"type": "tool_call", "name", "arguments"}
      {"type": "tool_result", "name", "result"}
      {"type": "token", "content"}
      {"type": "final", "content"}   累积的完整答复
    会原地修改 messages（追加 assistant / tool 消息），便于上层落库。
    """
    tools = registry.openai_schemas()

    for _ in range(settings.agent_max_steps):
        msg = await chat_once(messages, tools=tools)

        if not getattr(msg, "tool_calls", None):
            # 收敛到最终回答：再发一次流式请求获得逐字输出
            final_parts: list[str] = []
            async for token in chat_stream(messages):
                final_parts.append(token)
                yield {"type": "token", "content": token}
            final_text = "".join(final_parts) or (msg.content or "")
            if not final_parts and final_text:
                yield {"type": "token", "content": final_text}
            messages.append({"role": "assistant", "content": final_text})
            yield {"type": "final", "content": final_text}
            return

        # 有工具调用：先记录 assistant 消息，再逐个执行
        messages.append(_assistant_tool_call_message(msg))
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            yield {"type": "tool_call", "name": name, "arguments": args}

            tool = registry.get(name)
            if tool is None:
                result: Any = {"error": "unknown_tool", "name": name}
            else:
                try:
                    result = await tool.run(**args)
                except Exception as e:  # noqa: BLE001 工具异常不应中断循环
                    result = {"error": "tool_execution_failed", "detail": str(e)}

            yield {"type": "tool_result", "name": name, "result": result}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    # 超过最大步数仍未收敛
    fallback = "抱歉，处理该请求所需步骤过多，请简化问题后重试。"
    messages.append({"role": "assistant", "content": fallback})
    yield {"type": "token", "content": fallback}
    yield {"type": "final", "content": fallback}
