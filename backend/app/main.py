from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, session
from app.config import settings
from app.tools.internal_api import close_internal_client
from app.tools.registry import registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_internal_client()


app = FastAPI(title="内网多模态 AI 助手", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(session.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model": settings.llm_model,
        "tools": len(registry),
        "auth_enabled": settings.auth_enabled,
    }
