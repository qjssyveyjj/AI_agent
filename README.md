# 内网多模态 AI 助手

基于 [AI大模型架构.md](AI大模型架构.md) 实现的内网多模态智能助手：用户在网页上传截图并提问，多模态大模型识别图片内容，按需调用内部 `dev-api` 工具查询数据，最终生成自然语言答复。

## 架构

```
React 前端 (截图粘贴/上传, SSE 流式)
        │  HTTP
FastAPI 后端
  • JWT 鉴权  • 图片预处理  • 会话管理(Redis)
  • Agent 工具调用循环
        ├── OpenAI 兼容大模型端点 (Qwen3-VL-Plus, 支持 tools)
        └── 工具插件层 → 内部 dev-api (httpx, 认证/脱敏)
```

数据流：前端发送 `文本 + 图片(base64)` → 后端压缩图片并构造多模态消息 → 模型判断是否需要工具 → 若 `tool_calls` 则后端执行内部 API 并回灌结果 → 循环直至模型产出最终答复 → SSE 逐字返回前端。

## 目录结构

```
backend/                FastAPI 后端
  app/
    main.py             入口、CORS、路由
    config.py           pydantic-settings 配置
    api/                chat(SSE) / session / auth 路由
    core/               agent 循环 / llm 客户端 / 图片预处理
    tools/              工具插件框架 + 内部 API 客户端 + 示例工具
    session/            Redis 会话存储
    security/           JWT 鉴权
frontend/               React + Vite + TS 聊天界面
docker-compose.yml      backend / frontend / redis / postgres
```

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 配置后端环境变量（至少填写大模型端点）
cp backend/.env.example backend/.env
# 编辑 backend/.env，设置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL

# 2. 一键启动
docker compose up -d --build
```

- 前端：http://localhost:8080
- 后端健康检查：http://localhost:8000/api/health

### 方式二：本地开发

后端：

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 编辑大模型与 Redis 配置
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, 已配置 /api 代理到 8000
```

> 本地运行需可用的 Redis；可用 `docker run -p 6379:6379 redis:7-alpine` 快速启动。

## 关键配置（backend/.env）

| 变量 | 说明 |
| :-- | :-- |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | 已有的 OpenAI 兼容大模型端点 |
| `INTERNAL_API_BASE` / `INTERNAL_API_TOKEN` | 内部 dev-api 地址与认证 Token |
| `REDIS_URL` | 会话缓存 |
| `AGENT_MAX_STEPS` | Agent 循环最大步数（防失控） |
| `IMAGE_MAX_EDGE` / `IMAGE_JPEG_QUALITY` | 图片压缩：长边像素 / JPEG 质量 |
| `AUTH_ENABLED` | 是否开启 JWT 鉴权（开发态可设 false 放行匿名） |

## 新增内部 API 工具

工具层为插件式，新增一个内部接口只需两步，无需改动 Agent 循环：

1. 在 `backend/app/tools/` 下新建工具类，继承 `Tool`，定义 `name / description / parameters(JSON Schema)` 与 `async run()`，在 `run` 中通过 `call_internal_api()` 调用 dev-api 并按需脱敏。
2. 在 `backend/app/tools/registry.py` 中 `registry.register(YourTool())`。

参考示例 `backend/app/tools/example_order.py`（`query_order_status`）。当 dev-api 暂未接入时，该示例返回演示数据，便于端到端跑通。

> 若 dev-api 提供 OpenAPI/Swagger，可据此批量生成工具描述，大幅减少手工封装。

## 安全说明

- 内部 API 仅经后端代理，前端永不直连，避免内部接口被绕过。
- 模型无权直接访问内部 API，所有工具执行在后端可控范围内。
- 敏感字段（如手机号）在工具层脱敏后再送模型。
- 纯内网部署时，模型镜像/Python 包/模型权重需提前离线准备。

## 接口一览

| 方法 | 路径 | 说明 |
| :-- | :-- | :-- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/auth/login` | 演示登录，签发 JWT |
| POST | `/api/sessions` | 创建会话 |
| GET | `/api/sessions/{id}/messages` | 查询会话历史 |
| POST | `/api/chat` | 多模态对话，SSE 流式返回 |
