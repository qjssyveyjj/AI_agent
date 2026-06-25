from app.tools.base import Tool
from app.tools.example_order import QueryOrderStatusTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def openai_schemas(self) -> list[dict]:
        """生成注入大模型的 tools 描述数组。"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)


registry = ToolRegistry()

# 在此注册所有工具；新增内部 API 工具时追加一行即可
registry.register(QueryOrderStatusTool())
