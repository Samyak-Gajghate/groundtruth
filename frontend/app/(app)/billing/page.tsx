"use client";

import { useEffect, useState } from "react";
import {
  CreditCard,
  TrendingUp,
  Check,
  Zap,
  Crown,
  ArrowUpRight,
  Receipt,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Tier = "free" | "pro" | "enterprise";

const PLAN_META: Record<Tier, { icon: React.ReactNode; price: string; cadence: string; tagline: string; highlight: boolean; perks: string[] }> = {
  free: {
    icon: <Zap className="h-4 w-4" />,
    price: "$0",
    cadence: "forever",
    tagline: "Kick the tires, ship a demo, evaluate the product.",
    highlight: false,
    perks: ["1 admin seat", "5 documents", "1,000 messages / mo", "Mock billing", "Community Slack"],
  },
  pro: {
    icon: <Crown className="h-4 w-4" />,
    price: "$199",
    cadence: "per month, billed monthly",
    tagline: "For teams shipping AI support into real customer accounts.",
    highlight: true,
    perks: [
      "Up to 10 admin seats",
      "500 documents",
      "100,000 messages / mo",
      "Embed widget + REST API",
      "Per-tenant cost ledger",
      "OpenAI / Anthropic / Bedrock routing",
      "Email + Slack support",
    ],
  },
  enterprise: {
    icon: <CreditCard className="h-4 w-4" />,
    price: "Custom",
    cadence: "annual contract",
    tagline: "Bring-your-own keys, custom SLA, audit log retention.",
    highlight: false,
    perks: [
      "Unlimited seats",
      "Unlimited documents",
      "Pooled messages w/ overage",
      "SAML SSO + SCIM",
      "Data-residency picker",
      "Dedicated infra · 99.9% SLA",
      "Named CSM",
    ],
  },
};

export default function BillingPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.billingMe>> | null>(null);
  const [plans, setPlans] = useState<Awaited<ReturnType<typeof api.plans>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    try {
      const [b, p] = await Promise.all([api.billingMe(), api.plans()]);
      setData(b); setPlans(p);
    } catch (e) { setErr((e as Error).message); }
  }
  useEffect(() => { refresh(); }, []);

  async function upgrade(plan: string) {
    try {
      const cs = await api.checkout(plan, window.location.origin + "/billing");
      window.location.href = cs.url.startsWith("http") ? cs.url : (window.location.origin + cs.url);
    } catch (e) { setErr((e as Error).message); }
  }

  if (err) return <div className="p-6 text-rose-300">{err}</div>;
  if (!data || !plans) {
    return (
      <div className="p-6 grid gap-3 max-w-5xl mx-auto animate-slide-up">
        <div className="h-9 w-48 rounded-md bg-white/[0.04] animate-pulse" />
        <div className="grid grid-cols-3 gap-3"><div className="h-44 rounded-xl bg-white/[0.03] animate-pulse" /><div className="h-44 rounded-xl bg-white/[0.03] animate-pulse" /><div className="h-44 rounded-xl bg-white/[0.03] animate-pulse" /></div>
      </div>
    );
  }

  const used = data.used_messages_this_month;
  const cap = data.limits.messages;
  const usedPct = cap > 0 ? Math.min(100, (used / cap) * 100) : 0;
  const usedColor = usedPct > 90 ? "bg-rose-400" : usedPct > 70 ? "bg-amber-400" : "bg-emerald-400";

  const invoices = [
    { id: "INV-2026-05-001", date: "May 1, 2026", amount: 199.0, status: "paid" },
    { id: "INV-2026-04-001", date: "Apr 1, 2026", amount: 199.0, status: "paid" },
    { id: "INV-2026-03-001", date: "Mar 1, 2026", amount: 199.0, status: "paid" },
    { id: "INV-2026-02-001", date: "Feb 1, 2026", amount: 199.0, status: "paid" },
    { id: "INV-2026-01-001", date: "Jan 1, 2026", amount: 199.0, status: "paid" },
  ];

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto space-y-6 animate-slide-up">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
          <p className="text-sm text-subtle mt-1">
            Current plan{" "}
            <Badge variant={data.plan === "pro" ? "success" : data.plan === "enterprise" ? "violet" : "neutral"} dot>
              {data.plan.toUpperCase()}
            </Badge>{" "}
            · status <span className="text-zinc-200">{data.status}</span> · renews{" "}
            <span className="font-mono text-zinc-200">Jun 1, 2026</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.06] bg-surface/60 px-3 py-1.5 text-xs text-zinc-200 hover:bg-white/[0.06]">
            <Download className="h-3.5 w-3.5" /> Download W-9
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.06] bg-surface/60 px-3 py-1.5 text-xs text-zinc-200 hover:bg-white/[0.06]">
            Update payment
          </button>
        </div>
      </div>

      {/* Usage bar */}
      <Card>
        <CardHeader
          title="This month"
          subtitle="Resets on the 1st · billed in arrears at the listed cadence"
          action={
            <div className="flex items-center gap-1.5 text-2xs">
              <TrendingUp className="h-3 w-3 text-emerald-400" />
              <span className="text-zinc-300">On track</span>
            </div>
          }
        />
        <CardBody className="space-y-5">
          <div>
            <div className="flex items-end justify-between mb-2">
              <div>
                <div className="text-2xs uppercase tracking-wider text-subtle">Messages used</div>
                <div className="font-semibold text-xl mt-0.5 tabular-nums">
                  {used.toLocaleString()}{" "}
                  <span className="text-subtle font-normal text-base">/ {cap.toLocaleString()}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xs uppercase tracking-wider text-subtle">Cost this month</div>
                <div className="font-semibold text-xl mt-0.5 tabular-nums">${data.cost_usd_this_month.toFixed(2)}</div>
              </div>
            </div>
            <div className="h-2 w-full rounded-full bg-white/[0.04] overflow-hidden">
              <div className={`h-full rounded-full ${usedColor}`} style={{ width: `${usedPct}%` }} />
            </div>
            <div className="mt-1 flex items-center justify-between text-2xs text-subtle">
              <span>{usedPct.toFixed(1)}% of monthly allowance</span>
              <span>Overage billed at <span className="font-mono">$0.003 / msg</span></span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
            <UsageMini label="Documents" value={`${10} / ${data.limits.docs}`} pct={10 / data.limits.docs * 100} />
            <UsageMini label="Active widgets" value="3 / unlimited" pct={3} />
            <UsageMini label="Webhook calls" value="14,212 / 50,000" pct={28.4} />
            <UsageMini label="Embedding tokens" value="218.4M / 1B" pct={21.8} />
          </div>
        </CardBody>
      </Card>

      {/* Plans */}
      <div>
        <div className="text-2xs uppercase tracking-wider text-subtle mb-2 font-medium">Plans</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {(["free", "pro", "enterprise"] as Tier[]).map((tier) => {
            const meta = PLAN_META[tier];
            const isCurrent = data.plan === tier;
            const exists = plans.plans.find((p) => p.id === tier);
            return (
              <div
                key={tier}
                className={`relative rounded-xl border p-5 ${
                  meta.highlight
                    ? "border-emerald-500/30 bg-gradient-to-b from-emerald-500/[0.06] to-transparent shadow-glow"
                    : "border-white/[0.06] bg-surface/60"
                }`}
              >
                {meta.highlight ? (
                  <div className="absolute -top-2.5 left-5 inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-2xs font-medium text-emerald-300">
                    <Crown className="h-2.5 w-2.5" /> Most popular
                  </div>
                ) : null}
                <div className="flex items-center gap-2 text-zinc-200">
                  <span className={meta.highlight ? "text-emerald-400" : "text-zinc-400"}>{meta.icon}</span>
                  <span className="text-sm font-medium uppercase tracking-wider">{tier}</span>
                </div>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-3xl font-semibold tracking-tight">{meta.price}</span>
                  {tier !== "enterprise" ? (
                    <span className="text-xs text-subtle">/ mo</span>
                  ) : null}
                </div>
                <div className="text-2xs text-subtle">{meta.cadence}</div>
                <p className="mt-3 text-sm text-zinc-300 leading-relaxed">{meta.tagline}</p>
                <ul className="mt-4 space-y-1.5 text-sm">
                  {meta.perks.map((perk) => (
                    <li key={perk} className="flex items-start gap-2 text-zinc-300">
                      <Check className={`h-3.5 w-3.5 mt-1 flex-shrink-0 ${meta.highlight ? "text-emerald-400" : "text-zinc-500"}`} />
                      {perk}
                    </li>
                  ))}
                </ul>
                <button
                  disabled={isCurrent || !exists || tier === "free"}
                  onClick={() => upgrade(tier)}
                  className={`mt-5 w-full rounded-md py-2 text-sm font-medium disabled:opacity-40 ${
                    meta.highlight
                      ? "bg-emerald-500 text-zinc-950 hover:bg-emerald-400"
                      : "bg-zinc-50 text-zinc-950 hover:bg-white"
                  }`}
                >
                  {isCurrent ? "Current plan" : tier === "free" ? "Free forever" : tier === "enterprise" ? "Contact sales" : `Upgrade to ${tier}`}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invoices */}
      <Card>
        <CardHeader
          title="Invoices"
          subtitle="Paid invoices since account creation · auto-emailed to billing@acme.example"
          action={<button className="text-2xs text-subtle hover:text-zinc-100">View all <ArrowUpRight className="inline h-3 w-3" /></button>}
        />
        <div className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-2xs uppercase tracking-wider text-subtle bg-white/[0.02]">
                <th className="px-5 py-2.5 font-medium">Invoice</th>
                <th className="px-2 py-2.5 font-medium">Issue date</th>
                <th className="px-2 py-2.5 font-medium">Amount</th>
                <th className="px-2 py-2.5 font-medium">Status</th>
                <th className="px-5 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-300">
                        <Receipt className="h-4 w-4" />
                      </div>
                      <div className="font-mono text-xs text-zinc-200">{inv.id}</div>
                    </div>
                  </td>
                  <td className="px-2 py-3 text-zinc-300">{inv.date}</td>
                  <td className="px-2 py-3 font-mono text-zinc-200 tabular-nums">${inv.amount.toFixed(2)}</td>
                  <td className="px-2 py-3"><Badge variant="success" dot>{inv.status}</Badge></td>
                  <td className="px-5 py-3 text-right">
                    <button className="inline-flex items-center gap-1 text-xs text-zinc-300 hover:text-zinc-100">
                      <Download className="h-3 w-3" /> PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function UsageMini({ label, value, pct }: { label: string; value: string; pct: number }) {
  const color = pct > 90 ? "bg-rose-400" : pct > 70 ? "bg-amber-400" : "bg-emerald-400";
  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
      <div className="text-2xs uppercase tracking-wider text-subtle">{label}</div>
      <div className="text-sm font-medium mt-1 tabular-nums text-zinc-100">{value}</div>
      <div className="mt-1.5 h-1 rounded-full bg-white/[0.04] overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  );
}
