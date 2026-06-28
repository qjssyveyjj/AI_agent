export interface KbDoc {
  id: number;
  filename: string;
  source: string;
  size: number;
  status: string;
  chunk_count: number;
  created_at: string;
}

export async function uploadKbDocument(file: File): Promise<KbDoc> {
  const fd = new FormData();
  fd.append("file", file);
  const resp = await fetch("/api/kb/documents", { method: "POST", body: fd });
  if (!resp.ok) {
    let detail = `上传失败 (${resp.status})`;
    try {
      const j = await resp.json();
      if (j.detail) detail = j.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return resp.json();
}

export async function listKbDocuments(): Promise<KbDoc[]> {
  const resp = await fetch("/api/kb/documents");
  if (!resp.ok) throw new Error(`加载失败 (${resp.status})`);
  return (await resp.json()).documents as KbDoc[];
}

export async function deleteKbDocument(id: number): Promise<void> {
  const resp = await fetch(`/api/kb/documents/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`删除失败 (${resp.status})`);
}
