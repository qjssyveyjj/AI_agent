# 保丰港生产系统 AI 助手 — API 对接说明

> 本文档面向生产系统（192.168.126.200）开发人员，用于把 AI 助手能力集成到生产系统中。

## 一、整体说明

AI 助手是一个独立部署的后端服务，对外提供 HTTP / SSE 接口。生产系统有两种接入方式：

1. **直接调用 API**（推荐用于深度集成）：生产系统自己的前端/后端直接调用 `/api/chat`，自行渲染对话。
2. **嵌入聊天页面**（最省事）：用 `iframe` 把现成的聊天界面嵌入生产系统页面。

```
生产系统页面  ──(方式1: 调 API)──▶  AI 助手后端 (FastAPI)  ──▶ 大模型 + dev-api 工具
生产系统页面  ──(方式2: iframe)──▶  AI 助手前端页面
```

> 注意：AI 助手后端会反过来调用 `192.168.126.200/dev-api` 上的内部接口作为"工具"。请确保 AI 后端所在主机能访问 dev-api，并为其开通所需的接口与 Token。

---

## 二、服务地址（部署后由运维确认填写）

| 项 | 地址（示例，需替换为实际值） |
| :-- | :-- |
| AI 后端 API 根地址 | `http://<AI后端主机IP>:8000` |
| 在线接口文档(Swagger) | `http://<AI后端主机IP>:8000/docs` |
| OpenAPI 规范(JSON) | `http://<AI后端主机IP>:8000/openapi.json` |
| 健康检查 | `http://<AI后端主机IP>:8000/api/health` |
| AI 聊天前端页面（方式2 嵌入用） | `http://<AI前端主机IP>:8080/` |

> 建议运维给 AI 后端分配一个固定内网 IP 或域名，例如 `http://192.168.126.210:8000`，本文后续以 `{BASE}` 代指 API 根地址。

---

## 三、鉴权

- 鉴权方式：**Bearer Token (JWT)**，在请求头携带 `Authorization: Bearer <token>`。
- 是否强制鉴权由后端环境变量 `AUTH_ENABLED` 控制：
  - `AUTH_ENABLED=false`（默认/联调期）：可不带 Token，匿名调用。
  - `AUTH_ENABLED=true`（生产建议）：必须带有效 Token，否则返回 401。
- 获取 Token：`POST {BASE}/api/auth/login`（演示用；正式环境建议改造为对接保丰港统一认证/LDAP，由运维与我方确认）。

```bash
curl -X POST {BASE}/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"zhangsan","password":"xxx"}'
# 返回: {"access_token":"eyJhbG...","token_type":"bearer"}
```

---

## 四、接口清单

### 1. 健康检查

`GET {BASE}/api/health`

返回：
```json
{ "status": "ok", "model": "Qwen3-VL-Plus", "tools": 1, "auth_enabled": false }
```

### 2. 创建会话（可选）

`POST {BASE}/api/sessions`

- 说明：返回一个 `session_id` 用于多轮对话上下文记忆。**也可不调用此接口**，直接调 `/api/chat` 不传 `session_id`，系统会自动新建并在响应中回传。

返回：
```json
{ "session_id": "3f9a1c2b8d..." }
```

### 3. 查询会话历史（可选）

`GET {BASE}/api/sessions/{session_id}/messages`

返回该会话的完整消息列表。

### 4. 对话（核心接口，SSE 流式）

`POST {BASE}/api/chat`

请求体：

| 字段 | 类型 | 必填 | 说明 |
| :-- | :-- | :-- | :-- |
| `session_id` | string \| null | 否 | 多轮对话标识；不传则自动新建 |
| `text` | string | 否 | 用户问题文本 |
| `images` | string[] | 否 | 截图，元素为 `data:image/...;base64,xxx` 或纯 base64 字符串 |

> `text` 与 `images` 至少有一个非空。

请求示例：
```json
{
  "session_id": null,
  "text": "帮我查一下这个订单的最新物流状态",
  "images": ["data:image/png;base64,iVBORw0KGgo..."]
}
```

响应：`Content-Type: text/event-stream`（SSE），逐条推送事件，每条形如 `data: {json}\n\n`。

事件类型：

| `type` | 字段 | 含义 |
| :-- | :-- | :-- |
| `session` | `session_id` | 本轮使用的会话 ID（请保存，用于下一轮） |
| `tool_call` | `name`, `arguments` | AI 正在调用内部工具（可用于展示"正在查询…"） |
| `tool_result` | `name`, `result` | 工具返回结果 |
| `token` | `content` | 回答文本增量，逐字拼接显示 |
| `final` | `content` | 完整回答文本（token 拼接结果） |
| `done` | — | 本轮结束 |

事件流示例：
```
data: {"type":"session","session_id":"3f9a1c2b8d"}

data: {"type":"tool_call","name":"query_order_status","arguments":{"order_id":"ORD20260623-001"}}

data: {"type":"tool_result","name":"query_order_status","result":{"status":"运输中"}}

data: {"type":"token","content":"该订单"}

data: {"type":"token","content":"当前状态为运输中…"}

data: {"type":"final","content":"该订单当前状态为运输中，预计 6 月 26 日送达。"}

data: {"type":"done"}
```

---

## 五、对接方式一：直接调用 API（前端 JS 示例）

由于 `/api/chat` 是 POST + SSE，浏览器原生 `EventSource` 不支持，需用 `fetch` 流式读取：

```javascript
async function askAI({ text, images = [], sessionId = null, token }) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch("http://192.168.126.210:8000/api/chat", {
    method: "POST",
    headers,
    body: JSON.stringify({ session_id: sessionId, text, images }),
  });

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", answer = "", newSessionId = sessionId;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const ev = JSON.parse(line.slice(5).trim());
      if (ev.type === "session") newSessionId = ev.session_id;
      if (ev.type === "token") { answer += ev.content; /* 实时刷新到界面 */ }
    }
  }
  return { answer, sessionId: newSessionId };
}
```

把截图转 base64（生产系统页面里）：
```javascript
function fileToDataUrl(file) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}
```

后端语言（Java/.NET/Python 等）对接同理：POST JSON，按行读取 SSE 流，解析 `data:` 后的 JSON。

---

## 六、对接方式二：iframe 嵌入

最简单，无需写对接代码，直接在生产系统页面嵌入聊天界面：

```html
<iframe
  src="http://192.168.126.211:8080/"
  style="width:420px;height:640px;border:none;border-radius:12px;"
  title="保丰港生产系统AI助手">
</iframe>
```

可做成右下角悬浮按钮，点击弹出该 iframe。

---

## 七、需要运维/双方配合的事项

1. **网络互通**：开通生产系统主机 → AI 后端 `:8000` 的访问；以及 AI 后端 → `192.168.126.200/dev-api` 的访问。
2. **CORS**：若生产系统页面直接用 JS 跨域调 AI 后端，需把生产系统域名加入 AI 后端 `CORS_ORIGINS` 环境变量（或用同源反向代理）。
3. **大模型端点**：配置 AI 后端 `.env` 中的 `LLM_BASE_URL / LLM_API_KEY / LLM_MODEL`。
4. **内部工具接口**：提供 `dev-api` 需要被 AI 调用的接口清单（最好有 Swagger），以及调用所需的 `INTERNAL_API_TOKEN`。我方据此在工具层封装。
5. **鉴权方案**：确定正式环境是用本系统 JWT，还是对接保丰港统一认证。
6. **超时**：SSE 为长连接，若中间有 Nginx/网关，需关闭对 `/api/` 的缓冲（`proxy_buffering off`）并放大读超时。

---

## 八、最简交付清单（给生产系统人员）

只需告诉他们四样东西即可开始对接：

1. API 根地址：`http://<AI后端IP>:8000`
2. 在线文档：`http://<AI后端IP>:8000/docs`
3. 鉴权方式：`Authorization: Bearer <token>`（或联调期免鉴权）
4. 核心接口：`POST /api/chat`（SSE 流式，请求/事件格式见本文第四章）
