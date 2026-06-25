from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    工具基类。新增内部 API 工具时继承本类并在 registry 中注册即可，
    无需改动 Agent 循环。
    """

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """执行工具，返回可 JSON 序列化的结构化结果。"""
        raise NotImplementedError

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
