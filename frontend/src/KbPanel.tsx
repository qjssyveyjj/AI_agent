import { useCallback, useEffect, useRef, useState } from "react";
import { deleteKbDocument, listKbDocuments, uploadKbDocument, type KbDoc } from "./kbApi";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function KbPanel({ onClose }: { onClose: () => void }) {
  const [docs, setDocs] = useState<KbDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocs(await listKbDocuments());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onUpload = useCallback(
    async (files: FileList | File[]) => {
      setUploading(true);
      setError(null);
      try {
        for (const f of Array.from(files)) {
          await uploadKbDocument(f);
        }
        await refresh();
      } catch (e) {
        setError(String(e));
      } finally {
        setUploading(false);
      }
    },
    [refresh]
  );

  const onRemove = useCallback(
    async (id: number) => {
      try {
        await deleteKbDocument(id);
        setDocs((prev) => prev.filter((d) => d.id !== id));
      } catch (e) {
        setError(String(e));
      }
    },
    []
  );

  return (
    <div className="kb-overlay" onClick={onClose}>
      <div className="kb-modal" onClick={(e) => e.stopPropagation()}>
        <div className="kb-modal-head">
          <span className="kb-modal-title">生产系统知识库</span>
          <button className="kb-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        <div className="kb-toolbar">
          <button
            className="kb-upload-btn"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {uploading ? "入库中…" : "上传文档入库"}
          </button>
          <span className="kb-hint">支持 PDF / Word / Excel / TXT / Markdown</span>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.xlsx,.txt,.md,.csv,.json,.log"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) void onUpload(e.target.files);
              e.target.value = "";
            }}
          />
        </div>

        {error && <div className="kb-error">{error}</div>}

        <div className="kb-list">
          {loading ? (
            <div className="kb-empty">加载中…</div>
          ) : docs.length === 0 ? (
            <div className="kb-empty">知识库为空，先上传一些资料吧。</div>
          ) : (
            docs.map((d) => (
              <div className="kb-row" key={d.id}>
                <span className="doc-ico">
                  {d.filename.split(".").pop()?.toUpperCase() || "FILE"}
                </span>
                <span className="kb-row-meta">
                  <span className="kb-row-name">{d.filename}</span>
                  <span className="kb-row-sub">
                    {formatSize(d.size)} · {d.chunk_count} 片段 · {d.source}
                  </span>
                </span>
                <button className="kb-del" onClick={() => void onRemove(d.id)}>
                  删除
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
