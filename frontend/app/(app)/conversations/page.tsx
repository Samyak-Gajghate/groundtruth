"use client";

import { useEffect, useState } from "react";
import { Search, Globe, MessagesSquare, Bot, User2, FileText } from "lucide-react";
import { clsx } from "clsx";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Conv = Awaited<ReturnType<typeof api.listConversations>>[number];
type Active = Awaited<ReturnType<typeof api.getConversation>>;

export default function ConversationsPage() {
  const [list, setList] = useState<Conv[]>([]);
  const [active, setActive] = useState<Active | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.listConversations().then((cs) => {
      setList(cs);
      if (cs.length && !active) {
        api.getConversation(cs[0].id).then(setActive).catch(() => {});
      }
    }).catch((e) => setErr((e as Error).message));
  }, []);

  async function open(id: string) {
    try { setActive(await api.getConversation(id)); } catch (e) { setErr((e as Error).message); }
  }

  const filtered = list.filter((c) =>
    !q || (c.last_message_preview ?? "").toLowerCase().includes(q.toLowerCase()),
  );

  return (
    <div className="px-6 py-6 max-w-7xl mx-auto animate-slide-up">
      <div className="flex items-end justify-between mb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Conversations</h1>
          <p className="text-sm text-subtle mt-1">
            {list.length} total · grounded answers across widget, dashboard and API
          </p>
        </div>
        <div className="flex items-center gap-2 text-2xs text-subtle">
          <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> widget</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-violet-400" /> dashboard</span>
        </div>
      </div>

      {err ? <div className="rounded-md border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-300 mb-4">{err}</div> : null}

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4">
        <Card className="overflow-hidden flex flex-col max-h-[calc(100vh-220px)]">
          <div className="border-b border-white/[0.06] p-3">
            <div className="flex items-center gap-2 rounded-md border border-white/[0.06] bg-bg/50 px-2.5 py-1.5 text-sm">
              <Search className="h-3.5 w-3.5 text-subtle" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search conversations…"
                className="flex-1 bg-transparent outline-none placeholder:text-subtle text-zinc-100"
              />
            </div>
          </div>
          <div className="overflow-y-auto flex-1">
            {filtered.map((c) => {
              const isActive = active?.id === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => open(c.id)}
                  className={clsx(
                    "w-full text-left border-b border-white/[0.04] px-4 py-3 transition-colors",
                    isActive ? "bg-white/[0.05]" : "hover:bg-white/[0.02]",
                  )}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <Badge variant={c.channel === "widget" ? "success" : "violet"} dot>{c.channel}</Badge>
                    <span className="text-2xs text-subtle">{c.message_count} msg</span>
                  </div>
                  <div className="line-clamp-2 text-sm text-zinc-200 leading-snug">
                    {c.last_message_preview ?? "(no messages)"}
                  </div>
                  <div className="mt-1 text-2xs text-subtle font-mono">
                    {c.end_user_session.slice(0, 16)} · {new Date(c.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </div>
                </button>
              );
            })}
            {filtered.length === 0 ? (
              <div className="px-4 py-6 text-sm text-subtle">No matches.</div>
            ) : null}
          </div>
        </Card>

        <Card className="overflow-hidden flex flex-col max-h-[calc(100vh-220px)]">
          {active ? (
            <>
              <div className="border-b border-white/[0.06] px-5 py-3 flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-zinc-100">Conversation transcript</div>
                  <div className="text-2xs text-subtle font-mono">{active.id.slice(0, 8)} · {active.messages.length} messages</div>
                </div>
                <Badge variant="success" dot>resolved</Badge>
              </div>
              <div className="overflow-y-auto p-5 space-y-4">
                {active.messages.map((m) => {
                  const isUser = m.role === "user";
                  return (
                    <div key={m.id} className="flex gap-3">
                      <div className={clsx(
                        "flex h-7 w-7 items-center justify-center rounded-full shrink-0",
                        isUser
                          ? "bg-zinc-800 text-zinc-300"
                          : "bg-gradient-to-br from-emerald-500 to-sky-500 text-zinc-950",
                      )}>
                        {isUser ? <User2 className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-zinc-100">{isUser ? "Customer" : "Acme Assistant"}</span>
                          <span className="text-2xs text-subtle font-mono">{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                        </div>
                        <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">{m.content}</div>
                        {!isUser && m.citations?.items?.length ? (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {m.citations.items.map((c) => (
                              <span key={c.marker} className="inline-flex items-center gap-1 rounded-md bg-white/[0.04] px-2 py-0.5 text-2xs text-zinc-300">
                                <FileText className="h-3 w-3 text-emerald-400" />
                                {c.filename}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-subtle">
              <div className="flex flex-col items-center gap-2">
                <MessagesSquare className="h-8 w-8 text-zinc-700" />
                Pick a conversation on the left to view the transcript.
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
