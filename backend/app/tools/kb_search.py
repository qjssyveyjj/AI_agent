from typing import Any

from app.kb import service as kb_service
from app.tools.base import Tool


class KbSearchTool(Tool):
    """知识库检索工具：从生产系统资料库（制度、操作手册、设备参数等）检索相关片段。"""

    name = "kb_search"
    description = (
        "在生产系统知识库中检索与问题相关的资料片段。"
        "涉及制度规范、操作手册、设备参数、流程说明等知识性问题时使用。"
        "返回若干条带来源文件名的文本片段。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索关键词或问题"},
            "top_k": {
                "type": "integer",
                "description": "返回片段数量，默认 5",
            },
        },
        "required": ["query"],
    }

    async def run(self, query: str, top_k: int | None = None, **_: Any) -> dict[str, Any]:
        results = await kb_service.search(query, top_k=top_k)
        if not results:
            return {"hits": [], "message": "知识库中未检索到相关资料"}
        return {"hits": results}
