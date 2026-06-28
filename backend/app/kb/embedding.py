from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def get_embed_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.embed_base_url,
            api_key=settings.embed_api_key,
        )
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化。"""
    if not texts:
        return []
    resp = await get_embed_client().embeddings.create(
        model=settings.embed_model,
        input=texts,
    )
    return [item.embedding for item in resp.data]


async def embed_query(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0]
