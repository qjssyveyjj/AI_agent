import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { streamChat, type ChatEvent } from "./api";
import Dashboard from "./Dashboard";

interface ToolTrace {
  name: string;
  arguments?: Record<string, unknown>;
  result?: unknown;
}

interface Message {
  role: "user" | "assistant";
  text: string;
  images?: string[];
  files?: string[];
  tools?: ToolTrace[];
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface Conversation {
  id: string;
  title: string;
  sessionId: string | null;
  messages: Message[];
}

function newConversation(): Conversation {
  return {
    id: Math.random().toString(36).slice(2),
    title: "新对话",
    sessionId: null,
    messages: [],
  };
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([newConversation()]);
  const [activeId, setActiveId] = useState<string>(() => "");
  const [input, setInput] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [docs, setDocs] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);
  const attachRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeId && conversations[0]) setActiveId(conversations[0].id);
  }, [activeId, conversations]);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (attachRef.current && !attachRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? conversations[0],
    [conversations, activeId]
  );

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [active?.messages]);

  const patchActive = useCallback(
    (fn: (c: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((c) => (c.id === active.id ? fn(c) : c)));
    },
    [active?.id]
  );

  const addImages = useCallback(async (files: FileList | File[]) => {
    const urls: string[] = [];
    for (const f of Array.from(files)) {
      if (f.type.startsWith("image/")) urls.push(await fileToDataUrl(f));
    }
    if (urls.length) setImages((prev) => [...prev, ...urls]);
  }, []);

  const addDocs = useCallback((files: FileList | File[]) => {
    const list = Array.from(files).filter((f) => !f.type.startsWith("image/"));
    if (list.length) setDocs((prev) => [...prev, ...list]);
  }, []);

  const onPaste = useCallback(
    (e: React.ClipboardEvent) => {
      const files = Array.from(e.clipboardData.files);
      if (files.length) {
        e.preventDefault();
        void addImages(files);
      }
    },
    [addImages]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) void addImages(e.dataTransfer.files);
    },
    [addImages]
  );

  const createConversation = useCallback(() => {
    const conv = newConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setInput("");
    setImages([]);
    setDocs([]);
  }, []);

  const send = useCallback(async () => {
    if (sending || (!input.trim() && images.length === 0 && docs.length === 0)) return;
    const docNames = docs.map((f) => f.name);
    const fileNote = docNames.length ? `（附件：${docNames.join("、")}）` : "";
    const payloadText = [input, fileNote].filter(Boolean).join("\n");

    const userMsg: Message = {
      role: "user",
      text: input,
      images: [...images],
      files: docNames,
    };
    const assistantMsg: Message = { role: "assistant", text: "", tools: [] };
    const titleSeed =
      input.trim().slice(0, 18) || docNames[0] || (images.length ? "图片对话" : "新对话");

    patchActive((c) => ({
      ...c,
      title: c.messages.length === 0 ? titleSeed : c.title,
      messages: [...c.messages, userMsg, assistantMsg],
    }));
    setSending(true);

    const payloadImages = [...images];
    const convId = active.id;
    setInput("");
    setImages([]);
    setDocs([]);

    const updateAssistant = (fn: (m: Message) => Message) => {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c;
          const next = [...c.messages];
          next[next.length - 1] = fn(next[next.length - 1]);
          return { ...c, messages: next };
        })
      );
    };
    const setSessionId = (id: string) => {
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, sessionId: id } : c))
      );
    };

    try {
      for await (const ev of streamChat({
        session_id: active.sessionId,
        text: payloadText,
        images: payloadImages,
      })) {
        handleEvent(ev, updateAssistant, setSessionId);
      }
    } catch (err) {
      updateAssistant((m) => ({ ...m, text: m.text + `\n[错误] ${String(err)}` }));
    } finally {
      setSending(false);
    }
  }, [sending, input, images, docs, active, patchActive]);

  const stats = useMemo(() => {
    const messages = conversations.reduce((n, c) => n + c.messages.length, 0);
    const toolCalls = conversations.reduce(
      (n, c) => n + c.messages.reduce((m, msg) => m + (msg.tools?.length ?? 0), 0),
      0
    );
    return { conversations: conversations.length, messages, toolCalls };
  }, [conversations]);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo-dot" />
          <span className="brand-name">保丰港 · AI</span>
        </div>
        <button className="new-chat" onClick={createConversation}>
          + 新建对话
        </button>
        <div className="conv-list">
          {conversations.map((c) => (
            <button
              key={c.id}
              className={`conv-item ${c.id === active?.id ? "active" : ""}`}
              onClick={() => setActiveId(c.id)}
            >
              <span className="conv-dot" />
              <span className="conv-title">{c.title}</span>
              <span className="conv-count">{c.messages.length}</span>
            </button>
          ))}
        </div>
        <div className="sidebar-foot">内网私有化部署 · v0.1</div>
      </aside>

      <main className="center">
        <header className="header">
          <span className="title">保丰港生产系统AI助手</span>
          <span className="badge">Qwen3-VL · Agent</span>
        </header>
        <div className="messages" ref={scrollRef}>
          {(!active || active.messages.length === 0) && (
            <div className="empty">
              <div className="empty-orb" />
              <h2>保丰港生产系统 AI 助手</h2>
              <p>上传生产系统截图或描述问题，AI 将识别画面并调用内部系统作答。</p>
            </div>
          )}
          {active?.messages.map((m, i) => (
            <MessageBubble
              key={i}
              msg={m}
              thinking={
                sending &&
                i === active.messages.length - 1 &&
                m.role === "assistant" &&
                !m.text &&
                (m.tools?.length ?? 0) === 0
              }
            />
          ))}
        </div>

        <div
          className="composer"
          onPaste={onPaste}
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          {images.length > 0 && (
            <div className="thumbs">
              {images.map((src, i) => (
                <div className="thumb" key={i}>
                  <img src={src} alt="" />
                  <button onClick={() => setImages((p) => p.filter((_, idx) => idx !== i))}>
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          {docs.length > 0 && (
            <div className="doc-chips">
              {docs.map((f, i) => (
                <div className="doc-chip" key={i}>
                  <span className="doc-ico">{f.name.split(".").pop()?.toUpperCase() || "FILE"}</span>
                  <span className="doc-meta">
                    <span className="doc-name">{f.name}</span>
                    <span className="doc-size">{formatSize(f.size)}</span>
                  </span>
                  <button
                    className="doc-remove"
                    onClick={() => setDocs((p) => p.filter((_, idx) => idx !== i))}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="composer-row">
            <div className="attach" ref={attachRef}>
              <button
                type="button"
                className={`attach-btn ${menuOpen ? "open" : ""}`}
                aria-label="添加内容"
                onClick={() => setMenuOpen((v) => !v)}
              >
                +
              </button>
              {menuOpen && (
                <div className="attach-menu">
                  <button
                    type="button"
                    className="attach-menu-item"
                    onClick={() => {
                      fileInputRef.current?.click();
                      setMenuOpen(false);
                    }}
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                      <rect x="3" y="4" width="18" height="16" rx="2" fill="none" stroke="currentColor" strokeWidth="1.6" />
                      <circle cx="8.5" cy="9.5" r="1.6" fill="currentColor" />
                      <path d="M5 17l4.5-5 3 3.5L15.5 12 19 17" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                    </svg>
                    上传图片
                  </button>
                  <button
                    type="button"
                    className="attach-menu-item"
                    onClick={() => {
                      docInputRef.current?.click();
                      setMenuOpen(false);
                    }}
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                      <path d="M14 3v5h5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                      <path d="M8.5 13h7M8.5 16.5h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    </svg>
                    上传文件
                  </button>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                hidden
                onChange={(e) => {
                  if (e.target.files) void addImages(e.target.files);
                  e.target.value = "";
                }}
              />
              <input
                ref={docInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.ppt,.pptx"
                multiple
                hidden
                onChange={(e) => {
                  if (e.target.files) addDocs(e.target.files);
                  e.target.value = "";
                }}
              />
            </div>
            <textarea
              value={input}
              placeholder="输入问题，支持粘贴/拖拽截图…（Enter 发送，Shift+Enter 换行）"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button className="send-btn" disabled={sending} onClick={() => void send()}>
              {sending ? "…" : "发送"}
            </button>
          </div>
        </div>
      </main>

      <Dashboard stats={stats} />
    </div>
  );
}

function handleEvent(
  ev: ChatEvent,
  updateAssistant: (fn: (m: Message) => Message) => void,
  setSessionId: (id: string) => void
) {
  switch (ev.type) {
    case "session":
      if (ev.session_id) setSessionId(ev.session_id);
      break;
    case "token":
      updateAssistant((m) => ({ ...m, text: m.text + (ev.content ?? "") }));
      break;
    case "error":
      updateAssistant((m) => ({
        ...m,
        text: m.text + `\n[服务错误] ${ev.message ?? "未知错误"}`,
      }));
      break;
    case "tool_call":
      updateAssistant((m) => ({
        ...m,
        tools: [...(m.tools ?? []), { name: ev.name ?? "", arguments: ev.arguments }],
      }));
      break;
    case "tool_result":
      updateAssistant((m) => {
        const tools = [...(m.tools ?? [])];
        for (let i = tools.length - 1; i >= 0; i--) {
          if (tools[i].name === ev.name && tools[i].result === undefined) {
            tools[i] = { ...tools[i], result: ev.result };
            break;
          }
        }
        return { ...m, tools };
      });
      break;
    default:
      break;
  }
}

function MessageBubble({ msg, thinking }: { msg: Message; thinking?: boolean }) {
  return (
    <div className={`row ${msg.role}`}>
      <div className={`avatar ${msg.role}`}>{msg.role === "user" ? "你" : "AI"}</div>
      <div className={`bubble ${msg.role}`}>
        {msg.images?.map((src, i) => (
          <img className="msg-img" key={i} src={src} alt="" />
        ))}
        {msg.files && msg.files.length > 0 && (
          <div className="msg-files">
            {msg.files.map((name, i) => (
              <div className="msg-file" key={i}>
                <span className="doc-ico">{name.split(".").pop()?.toUpperCase() || "FILE"}</span>
                <span className="doc-name">{name}</span>
              </div>
            ))}
          </div>
        )}
        {msg.tools?.map((t, i) => (
          <div className="tool-trace" key={i}>
            <span className="tool-name">调用工具 · {t.name}</span>
            {t.arguments && <code>{JSON.stringify(t.arguments)}</code>}
            {t.result !== undefined && <pre>{JSON.stringify(t.result, null, 2)}</pre>}
          </div>
        ))}
        {msg.text && <div className="text">{msg.text}</div>}
        {thinking && (
          <div className="typing">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
    </div>
  );
}
