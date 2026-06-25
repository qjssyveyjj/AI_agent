import json
import time
import uuid

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _key(session_id: str) -> str:
    return f"session:{session_id}:messages"


def _meta_key(session_id: str) -> str:
    return f"session:{session_id}:meta"


async def create_session(user: str) -> str:
    session_id = uuid.uuid4().hex
    r = get_redis()
    meta = {"user": user, "created_at": time.time()}
    await r.set(_meta_key(session_id), json.dumps(meta), ex=settings.session_ttl_seconds)
    return session_id


async def session_exists(session_id: str) -> bool:
    return bool(await get_redis().exists(_meta_key(session_id)))


async def append_message(session_id: str, message: dict) -> None:
    r = get_redis()
    await r.rpush(_key(session_id), json.dumps(message, ensure_ascii=False))
    await r.expire(_key(session_id), settings.session_ttl_seconds)
    await r.expire(_meta_key(session_id), settings.session_ttl_seconds)


async def get_messages(session_id: str) -> list[dict]:
    raw = await get_redis().lrange(_key(session_id), 0, -1)
    return [json.loads(item) for item in raw]
