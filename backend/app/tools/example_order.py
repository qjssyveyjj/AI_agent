from typing import Any

from app.tools.base import Tool
from app.tools.internal_api import call_internal_api


def _mask_phone(value: str) -> str:
    """敏感字段脱敏：手机号中间 4 位掩码。"""
    if isinstance(value, str) and len(value) == 11 and value.isdigit():
        return value[:3] + "****" + value[7:]
    return value


class QueryOrderStatusTool(Tool):
    """
    示例工具：根据订单号查询订单状态。
    真实 dev-api 规范确定后，仅需调整 path/params 与脱敏字段即可。
    当内部 API 不可用时返回演示数据，保证端到端流程可跑通。
    """

    name = "query_order_status"
    description = "根据订单号查询订单的状态及详细信息（含物流、金额等）"
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "订单号，一般为 ORD 开头，例如 ORD20260623-001",
            }
        },
        "required": ["order_id"],
    }

    async def run(self, order_id: str, **_: Any) -> dict[str, Any]:
        result = await call_internal_api(
            "GET", "/order/status", params={"orderId": order_id}
        )

        if "error" in result:
            # dev-api 尚未接入时的演示数据
            result = {
                "demo": True,
                "orderId": order_id,
                "status": "运输中",
                "amount": 1299.00,
                "logistics": {"carrier": "顺丰", "eta": "2026-06-26", "trace": "已到达分拨中心"},
                "contactPhone": "13812345678",
            }

        if "contactPhone" in result:
            result["contactPhone"] = _mask_phone(result["contactPhone"])
        return result
