import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.agent import SYSTEM_PROMPT, build_user_message, run_agent
from app.core.image import preprocess_image_to_data_url
from app.security.auth import get_current_user
from app.session import store

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("ai_agent.chat")


class ChatRequest(BaseModel):
    session_id: str | None = None
    text: str = ""
    images: list[str] = Field(default_factory=list)  # data URL 或纯 base64


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest, user: str = Depends(get_current_user)) -> StreamingResponse:
    session_id = req.session_id
    if not session_id or not await store.session_exists(session_id):
        session_id = await store.create_session(user)

    processed_images = [preprocess_image_to_data_url(img) for img in req.images]
    user_message = build_user_message(req.text, processed_images)

    history = await store.get_messages(session_id)
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append(user_message)

    await store.append_message(session_id, user_message)

    async def event_stream() -> AsyncIterator[str]:
        yield _sse({"type": "session", "session_id": session_id})
        # run_agent 会原地向 messages 追加 assistant/tool 消息
        start_len = len(messages)
        try:
            async for event in run_agent(messages):
                yield _sse(event)
        except Exception as e:  # noqa: BLE001 避免异常直接中断 SSE 连接（前端会显示 network error）
            logger.exception("agent 执行失败")
            yield _sse(
                {
                    "type": "error",
                    "message": f"模型服务调用失败：{type(e).__name__}: {e}",
                }
            )
        else:
            # 仅在成功时落库本轮新增的非用户消息（assistant / tool）
            for msg in messages[start_len:]:
                await store.append_message(session_id, msg)
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
