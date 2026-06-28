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
    """批量向量化。按 embed_batch_size 分批（DashScope 单次输入条数有上限），
    并显式指定 dimensions 以保证返回维度与库表列一致。"""
    if not texts:
        return []

    client = get_embed_client()
    batch = max(1, settings.embed_batch_size)
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch):
        resp = await client.embeddings.create(
            model=settings.embed_model,
            input=texts[i : i + batch],
            dimensions=settings.embed_dim,
        )
        vectors.extend(item.embedding for item in resp.data)
    return vectors


async def embed_query(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0]
