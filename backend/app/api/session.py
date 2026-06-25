from fastapi import APIRouter, Depends, HTTPException

from app.security.auth import get_current_user
from app.session import store

router = APIRouter(prefix="/api/sessions", tags=["session"])


@router.post("")
async def create_session(user: str = Depends(get_current_user)) -> dict:
    session_id = await store.create_session(user)
    return {"session_id": session_id}


@router.get("/{session_id}/messages")
async def get_history(
    session_id: str, user: str = Depends(get_current_user)
) -> dict:
    if not await store.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    return {"session_id": session_id, "messages": await store.get_messages(session_id)}
