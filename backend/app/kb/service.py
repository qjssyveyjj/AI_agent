from typing import Any

from sqlalchemy import delete, select

from app.config import settings
from app.kb.chunker import chunk_text
from app.kb.db import get_sessionmaker
from app.kb.embedding import embed_query, embed_texts
from app.kb.models import KbChunk, KbDocument
from app.kb.parser import extract_text


async def ingest_document(filename: str, data: bytes, source: str = "upload") -> dict[str, Any]:
    """解析 -> 分块 -> 向量化 -> 入库。返回文档摘要。"""
    text = extract_text(filename, data)
    return await ingest_text(filename, text, source=source, size=len(data))


async def ingest_text(
    title: str, text: str, source: str = "upload", size: int | None = None
) -> dict[str, Any]:
    """将纯文本分块向量化入库（供 MCP / 直接文本入库使用）。"""
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("文档解析后无有效文本内容")

    vectors = await embed_texts(chunks)
    byte_size = size if size is not None else len(text.encode("utf-8"))

    sm = get_sessionmaker()
    async with sm() as session:
        doc = KbDocument(
            filename=title,
            source=source,
            size=byte_size,
            status="ready",
            chunk_count=len(chunks),
        )
        session.add(doc)
        await session.flush()  # 拿到 doc.id

        for seq, (content, vec) in enumerate(zip(chunks, vectors)):
            session.add(
                KbChunk(document_id=doc.id, seq=seq, content=content, embedding=vec)
            )
        await session.commit()
        return {
            "id": doc.id,
            "filename": doc.filename,
            "source": doc.source,
            "size": doc.size,
            "chunk_count": doc.chunk_count,
        }


async def search(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    """向量相似度检索，返回 Top-K 片段（含来源文件名与相似度）。"""
    top_k = top_k or settings.kb_top_k
    qvec = await embed_query(query)

    sm = get_sessionmaker()
    async with sm() as session:
        # 余弦距离 <=> ，距离越小越相似；score = 1 - distance
        distance = KbChunk.embedding.cosine_distance(qvec).label("distance")
        stmt = (
            select(KbChunk.content, KbDocument.filename, distance)
            .join(KbDocument, KbChunk.document_id == KbDocument.id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await session.execute(stmt)).all()

    results: list[dict[str, Any]] = []
    for content, filename, dist in rows:
        score = 1.0 - float(dist)
        if score < settings.kb_min_score:
            continue
        results.append({"source": filename, "score": round(score, 4), "content": content})
    return results


async def list_documents() -> list[dict[str, Any]]:
    sm = get_sessionmaker()
    async with sm() as session:
        stmt = select(KbDocument).order_by(KbDocument.created_at.desc())
        docs = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "source": d.source,
                "size": d.size,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]


async def delete_document(doc_id: int) -> bool:
    sm = get_sessionmaker()
    async with sm() as session:
        result = await session.execute(delete(KbDocument).where(KbDocument.id == doc_id))
        await session.commit()
        return result.rowcount > 0
