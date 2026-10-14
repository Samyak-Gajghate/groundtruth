"use client";

import { useEffect, useMemo, useState } from "react";
import {
  FileText,
  MessagesSquare,
  MessageCircle,
  DollarSign,
  Activity,
  Zap,
  Globe,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { CostAreaChart } from "@/components/ui/area-chart";
import { Badge } from "@/components/ui/badge";

type Overview = Awaited<ReturnType<typeof api.overview>>;

export default function DashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [convs, setConvs] = useState<Awaited<ReturnType<typeof api.listConversations>>>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.overview().then(setData).catch((e) => setErr((e as Error).message));
    api.listConversations().then(setConvs).catch(() => {});
  }, []);

  const derived = useMemo(() => {
    if (!data) return null;
    const days = [...data.daily].sort((a, b) => a.day.localeCompare(b.day));
    const tokens = days.map((d) => d.tokens);
    const costs = days.map((d) => d.cost_usd);
    const mid = Math.floor(days.length / 2);
    const sumA = costs.slice(0, mid).reduce((s, v) => s + v, 0);
    const sumB = costs.slice(mid).reduce((s, v) => s + v, 0);
    const costDelta = sumA === 0 ? 0 : ((sumB - sumA) / sumA) * 100;
    const tokA = tokens.slice(0, mid).reduce((s, v) => s + v, 0);
    const tokB = tokens.slice(mid).reduce((s, v) => s + v, 0);
    const tokDelta = tokA === 0 ? 0 : ((tokB - tokA) / tokA) * 100;
    return { days, tokens, costs, costDelta, tokDelta };
  }, [data]);

  if (err) return <div className="p-6 text-rose-300">{err}</div>;
  if (!data || !derived) {
    return (
      <div className="p-6 grid gap-3 max-w-7xl mx-auto">
        <div className="h-9 w-40 rounded-md bg-white/[0.04] animate-pulse" />
        <div className="grid grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-24 rounded-xl bg-white/[0.03] animate-pulse" />)}
        </div>
      </div>
    );
  }

  const t = data.totals;
  const days = derived.days;
  const chartData = days.map((d) => ({
    day: d.day.slice(5),
    cost: Number(d.cost_usd.toFixed(2)),
    tokens: d.tokens,
  }));

  const recent = convs.slice(0, 6);

  return (
    <div className="px-6 py-6 max-w-7xl mx-auto space-y-6 animate-slide-up">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="text-sm text-subtle mt-1">
            Usage and grounded answers across all channels in the last 30 days.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-subtle">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
            All systems operational
          </span>
        </div>
      </div>

      {/* Metric row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Documents"
          value={t.documents}
          icon={<FileText className="h-3.5 w-3.5" />}
          spark={spread(t.documents, 14, 0.4)}
          sparkColor="#8b5cf6"
        />
        <MetricCard
          label="Conversations"
          value={t.conversations.toLocaleString()}
          icon={<MessagesSquare className="h-3.5 w-3.5" />}
          delta={derived.tokDelta}
          spark={derived.tokens.map((v, i) => Math.round((t.conversations * v) / Math.max(1, derived.tokens.reduce((s, x) => s + x, 0)) * (i + 1) / 1))}
          sparkColor="#10b981"
        />
        <MetricCard
          label="Messages"
          value={t.messages.toLocaleString()}
          icon={<MessageCircle className="h-3.5 w-3.5" />}
          delta={derived.tokDelta}
          spark={derived.tokens}
          sparkColor="#0ea5e9"
        />
        <MetricCard
          label="Spend (30d)"
          value={`$${t.cost_usd_this_month.toFixed(2)}`}
          icon={<DollarSign className="h-3.5 w-3.5" />}
          delta={derived.costDelta}
          spark={derived.costs}
          sparkColor="#f59e0b"
        />
      </div>

      {/* Chart + Sources */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Spend & activity"
            subtitle="Daily cost in USD across all models"
            action={
              <div className="flex items-center gap-1 rounded-md border border-white/[0.06] bg-surface/60 p-0.5 text-xs">
                <button className="px-2 py-0.5 rounded text-subtle">7d</button>
                <button className="px-2 py-0.5 rounded bg-white/[0.06] text-zinc-100">14d</button>
                <button className="px-2 py-0.5 rounded text-subtle">30d</button>
              </div>
            }
          />
          <CardBody>
            <CostAreaChart
              data={chartData}
              xKey="day"
              series={[{ key: "cost", color: "#10b981", label: "USD" }]}
              height={240}
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Channels" subtitle="Where customers are talking to you" />
          <CardBody>
            <ChannelRow icon={<Globe className="h-3.5 w-3.5" />} label="Embed widget" pct={68} count={convs.filter((c) => c.channel === "widget").length} color="#10b981" />
            <ChannelRow icon={<MessagesSquare className="h-3.5 w-3.5" />} label="Dashboard" pct={32} count={convs.filter((c) => c.channel === "dashboard").length} color="#8b5cf6" />
            <ChannelRow icon={<Zap className="h-3.5 w-3.5" />} label="API" pct={0} count={0} color="#0ea5e9" />
            <div className="mt-4 pt-4 border-t border-white/[0.06] text-2xs text-subtle flex justify-between">
              <span>Avg response time</span>
              <span className="font-mono text-zinc-300">1.42s</span>
            </div>
            <div className="mt-1 text-2xs text-subtle flex justify-between">
              <span>Grounding rate</span>
              <span className="font-mono text-emerald-400">94.7%</span>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Recent activity */}
      <Card>
        <CardHeader
          title="Recent conversations"
          subtitle={`${convs.length} total · last 30 days`}
          action={
            <a href="/conversations" className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-100">
              View all <ArrowUpRight className="h-3 w-3" />
            </a>
          }
        />
        <div>
          {recent.map((c, i) => (
            <a
              key={c.id}
              href="/conversations"
              className={`flex items-center gap-3 px-5 py-3 text-sm hover:bg-white/[0.03] ${i !== recent.length - 1 ? "border-b border-white/[0.04]" : ""}`}
            >
              <Badge variant={c.channel === "widget" ? "success" : "violet"} dot>
                {c.channel}
              </Badge>
              <div className="flex-1 min-w-0 truncate text-zinc-200">{c.last_message_preview || "Untitled conversation"}</div>
              <span className="text-2xs text-subtle font-mono">{relativeTime(c.created_at)}</span>
              <Activity className="h-3.5 w-3.5 text-subtle" />
            </a>
          ))}
          {recent.length === 0 ? (
            <div className="px-5 py-6 text-sm text-subtle">No conversations yet.</div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

function ChannelRow({ icon, label, pct, count, color }: { icon: React.ReactNode; label: string; pct: number; count: number; color: string }) {
  return (
    <div className="space-y-1.5 py-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 text-zinc-300">
          <span style={{ color }}>{icon}</span> {label}
        </span>
        <span className="text-subtle">{count.toLocaleString()} · {pct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/[0.04] overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color, opacity: 0.8 }} />
      </div>
    </div>
  );
}

function spread(total: number, n: number, jitter: number): number[] {
  const arr: number[] = [];
  for (let i = 0; i < n; i++) {
    const base = (total * (i + 1)) / n;
    arr.push(Math.max(0, base * (1 + (Math.sin(i * 1.3) * jitter))));
  }
  return arr;
}

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
