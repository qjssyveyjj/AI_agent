"""
知识库 MCP Server（可选第二阶段）。

把生产系统知识库的检索/入库能力，通过 MCP 协议暴露为标准工具，
供 Cursor 等任意 MCP 客户端复用；同时本项目 AI 后端也可作为 MCP 客户端接入。

复用 app.kb.service 的检索/入库逻辑，与 PostgreSQL+pgvector 共用同一份数据。

运行（在 backend 目录下，使用含 mcp 依赖的环境）：
    python -m kb_mcp_server.server          # stdio 传输（供本地 MCP 客户端）

依赖见 kb_mcp_server/requirements.txt（独立环境，避免与 FastAPI 的 starlette 版本冲突）。
"""

from mcp.server.fastmcp import FastMCP

from app.kb import service as kb_service
from app.kb.db import init_kb

mcp = FastMCP("baofeng-kb")


@mcp.tool()
async def kb_search(query: str, top_k: int = 5) -> list[dict]:
    """在生产系统知识库中检索相关资料片段，返回带来源文件名与相似度的文本片段。"""
    return await kb_service.search(query, top_k=top_k)


@mcp.tool()
async def kb_add_text(title: str, content: str) -> dict:
    """将一段纯文本资料加入知识库（标题作为来源名）。"""
    return await kb_service.ingest_text(title, content, source="mcp")


@mcp.tool()
async def kb_list_documents() -> list[dict]:
    """列出知识库中已入库的文档。"""
    return await kb_service.list_documents()


def main() -> None:
    import asyncio

    asyncio.run(init_kb())
    mcp.run()  # 默认 stdio 传输


if __name__ == "__main__":
    main()
