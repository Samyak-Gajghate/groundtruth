"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Loader2,
  Trash2,
  Upload,
  Search,
  FileText,
  FileType2,
  Filter,
  ArrowUpDown,
  CheckCircle2,
  FileCode,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Doc = Awaited<ReturnType<typeof api.listDocs>>[number];

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");

  async function refresh() {
    try { setDocs(await api.listDocs()); } catch (e) { setErr((e as Error).message); }
  }
  useEffect(() => { refresh(); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setErr(null);
    try { await api.uploadDoc(file); await refresh(); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); e.target.value = ""; }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this document?")) return;
    await api.deleteDoc(id);
    await refresh();
  }

  const filtered = useMemo(
    () => docs.filter((d) => !q || d.filename.toLowerCase().includes(q.toLowerCase())),
    [docs, q],
  );

  const totalSize = docs.reduce((s, d) => s + d.byte_size, 0);
  const totalChunks = docs.reduce((s, d) => s + d.chunk_count, 0);

  return (
    <div className="px-6 py-6 max-w-7xl mx-auto space-y-6 animate-slide-up">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-subtle mt-1">
            {docs.length} indexed · {totalChunks.toLocaleString()} chunks · {(totalSize / 1024).toFixed(1)} KB total
          </p>
        </div>
        <label className="inline-flex items-center gap-2 rounded-md bg-zinc-50 text-zinc-950 text-sm font-medium px-3 py-1.5 cursor-pointer hover:bg-white shadow-glow">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {busy ? "Uploading…" : "Upload document"}
          <input type="file" accept="application/pdf,text/plain,text/markdown" className="hidden" onChange={onUpload} disabled={busy} />
        </label>
      </div>

      {err ? <div className="rounded-md border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">{err}</div> : null}

      <Card>
        <div className="flex items-center gap-2 border-b border-white/[0.06] px-4 py-2.5">
          <div className="flex items-center gap-2 flex-1 max-w-sm rounded-md border border-white/[0.06] bg-bg/50 px-2.5 py-1 text-sm">
            <Search className="h-3.5 w-3.5 text-subtle" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter by filename"
              className="flex-1 bg-transparent outline-none placeholder:text-subtle text-zinc-100"
            />
          </div>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.06] px-2.5 py-1 text-xs text-zinc-300 hover:bg-white/[0.04]">
            <Filter className="h-3 w-3" /> All types
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.06] px-2.5 py-1 text-xs text-zinc-300 hover:bg-white/[0.04]">
            <ArrowUpDown className="h-3 w-3" /> Newest
          </button>
        </div>

        <div className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-2xs uppercase tracking-wider text-subtle bg-white/[0.02]">
                <th className="px-5 py-2.5 font-medium">Document</th>
                <th className="px-2 py-2.5 font-medium">Status</th>
                <th className="px-2 py-2.5 font-medium">Pages</th>
                <th className="px-2 py-2.5 font-medium">Chunks</th>
                <th className="px-2 py-2.5 font-medium">Size</th>
                <th className="px-2 py-2.5 font-medium">Uploaded</th>
                <th className="px-5 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => {
                const ext = d.filename.split(".").pop()?.toLowerCase() ?? "";
                const Icon = ext === "md" ? FileCode : ext === "pdf" ? FileText : FileType2;
                const iconColor = ext === "pdf" ? "text-rose-400" : ext === "md" ? "text-emerald-400" : "text-sky-400";
                return (
                  <tr key={d.id} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-md bg-white/[0.04] ${iconColor}`}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="text-zinc-100 font-medium">{d.filename}</div>
                          <div className="text-2xs text-subtle font-mono">{d.id.slice(0, 8)}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-2 py-3">
                      <Badge variant="success" dot>
                        <CheckCircle2 className="h-2.5 w-2.5" /> Indexed
                      </Badge>
                    </td>
                    <td className="px-2 py-3 font-mono text-zinc-300">{d.page_count ?? "—"}</td>
                    <td className="px-2 py-3 font-mono text-zinc-300">{d.chunk_count}</td>
                    <td className="px-2 py-3 font-mono text-zinc-300">{(d.byte_size / 1024).toFixed(1)} KB</td>
                    <td className="px-2 py-3 text-zinc-400 text-xs">{new Date(d.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => onDelete(d.id)} className="text-subtle hover:text-rose-400">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-sm text-subtle">No documents match.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
