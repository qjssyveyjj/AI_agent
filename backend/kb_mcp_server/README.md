# 知识库 MCP Server（可选）

把生产系统知识库（PostgreSQL + pgvector）通过 MCP 协议暴露为标准工具，供 Cursor 等任意 MCP 客户端复用。

## 为什么独立环境

`mcp` 依赖的 `starlette` 版本与主后端的 FastAPI 不兼容，因此本 MCP Server 用**独立虚拟环境**运行，不影响主后端。它只复用 `app.kb` 的检索/入库逻辑，与主后端共享同一套 `DATABASE_URL` / `EMBED_*` 配置（同一份向量数据）。

## 安装与运行

在 `backend` 目录下：

```bash
python -m venv .venv-mcp
.venv-mcp\Scripts\activate        # Windows
pip install -r kb_mcp_server/requirements.txt

# 确保 .env 中 DATABASE_URL / EMBED_* 配置正确
python -m kb_mcp_server.server
```

默认使用 stdio 传输。

## 暴露的 MCP 工具

- `kb_search(query, top_k=5)`：检索知识库，返回带来源与相似度的片段。
- `kb_add_text(title, content)`：将一段纯文本加入知识库。
- `kb_list_documents()`：列出已入库文档。

## 在 Cursor 中接入（示例）

在 Cursor 的 `mcp.json` 中添加：

```json
{
  "mcpServers": {
    "baofeng-kb": {
      "command": "C:/AI_agent/backend/.venv-mcp/Scripts/python.exe",
      "args": ["-m", "kb_mcp_server.server"],
      "cwd": "C:/AI_agent/backend"
    }
  }
}
```
