from app.config import settings


def chunk_text(
    text: str, size: int | None = None, overlap: int | None = None
) -> list[str]:
    """
    按字符长度切分文本，块间保留重叠以避免语义截断。
    优先在段落/换行边界附近切，减少把句子切断的概率。
    """
    size = size or settings.kb_chunk_size
    overlap = overlap or settings.kb_chunk_overlap

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if len(normalized) <= size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    n = len(normalized)
    while start < n:
        end = min(start + size, n)
        if end < n:
            # 尝试在窗口后段的换行处断开，使分块更自然
            window = normalized[start:end]
            cut = max(window.rfind("\n"), window.rfind("。"), window.rfind("."))
            if cut > size * 0.5:
                end = start + cut + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
