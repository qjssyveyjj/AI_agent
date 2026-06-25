export interface ChatEvent {
  type: "session" | "tool_call" | "tool_result" | "token" | "final" | "done";
  session_id?: string;
  name?: string;
  arguments?: Record<string, unknown>;
  result?: unknown;
  content?: string;
}

export interface ChatPayload {
  session_id: string | null;
  text: string;
  images: string[];
}

/**
 * 通过 fetch 流式读取后端 SSE（POST 无法用 EventSource，需手动解析）。
 */
export async function* streamChat(
  payload: ChatPayload,
  token?: string
): AsyncGenerator<ChatEvent> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch("/api/chat", {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`请求失败: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        yield JSON.parse(json) as ChatEvent;
      } catch {
        // 忽略无法解析的分片
      }
    }
  }
}
