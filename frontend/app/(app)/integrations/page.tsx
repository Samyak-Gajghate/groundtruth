"use client";

import { Slack, Github, Mail, Webhook, Database, ArrowUpRight, Plug } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Integration = {
  name: string;
  provider: string;
  category: "Routing" | "Identity" | "CRM" | "Help desk" | "Notify" | "Source" | "Telemetry";
  description: string;
  status: "connected" | "available" | "beta";
  icon: React.ReactNode;
  accent: string;
  meta?: string;
};

const INTEGRATIONS: Integration[] = [
  { name: "Slack", provider: "slack.com", category: "Notify",
    description: "Get a thread in #support when a customer chat needs human escalation, or when the widget answers below a confidence threshold.",
    status: "connected", icon: <Slack className="h-5 w-5" />, accent: "bg-violet-500/10 text-violet-300",
    meta: "→ #support · 218 events / 30d" },
  { name: "Zendesk", provider: "zendesk.com", category: "Help desk",
    description: "Auto-create a Zendesk ticket on chat escalation. Round-trips agent replies back to the widget transcript.",
    status: "connected", icon: <Plug className="h-5 w-5" />, accent: "bg-emerald-500/10 text-emerald-300",
    meta: "12 tickets created / 7d" },
  { name: "Salesforce", provider: "salesforce.com", category: "CRM",
    description: "Resolve the end_user_session against a Salesforce Contact. Persist the conversation as an Activity on the matched Lead.",
    status: "connected", icon: <Plug className="h-5 w-5" />, accent: "bg-sky-500/10 text-sky-300",
    meta: "8,419 contacts mapped" },
  { name: "GitHub", provider: "github.com", category: "Source",
    description: "Ingest issues + discussions as documents. Re-index on commit. Optionally surface PR descriptions in answers.",
    status: "connected", icon: <Github className="h-5 w-5" />, accent: "bg-zinc-500/10 text-zinc-300",
    meta: "acme/support-docs · 14 syncs" },
  { name: "Notion", provider: "notion.so", category: "Source",
    description: "Sync a Notion workspace as a continuous source of docs. Honors page-level permissions when re-routed through the widget.",
    status: "available", icon: <Plug className="h-5 w-5" />, accent: "bg-zinc-500/10 text-zinc-300" },
  { name: "Confluence", provider: "atlassian.com", category: "Source",
    description: "Pull Confluence spaces. Filter on page properties to scope which spaces feed which widget.",
    status: "available", icon: <Plug className="h-5 w-5" />, accent: "bg-blue-500/10 text-blue-300" },
  { name: "Intercom", provider: "intercom.com", category: "Help desk",
    description: "Co-pilot for Intercom agents. Suggested replies grounded in your docs, posted as private notes for one-click approval.",
    status: "beta", icon: <Plug className="h-5 w-5" />, accent: "bg-blue-500/10 text-blue-300" },
  { name: "HubSpot", provider: "hubspot.com", category: "CRM",
    description: "Conversation transcripts ship to HubSpot timeline. Lead-scoring uses faithfulness + question-novelty signals.",
    status: "available", icon: <Plug className="h-5 w-5" />, accent: "bg-orange-500/10 text-orange-300" },
  { name: "Okta · SAML SSO", provider: "okta.com", category: "Identity",
    description: "SP-initiated SSO for admin login. Maps Okta groups to workspace roles. Enterprise plan.",
    status: "connected", icon: <Plug className="h-5 w-5" />, accent: "bg-indigo-500/10 text-indigo-300",
    meta: "32 users SSO'd" },
  { name: "PagerDuty", provider: "pagerduty.com", category: "Notify",
    description: "Page on-call when widget grounding drops below 0.85 sustained for 5+ minutes, or when API error rate spikes.",
    status: "available", icon: <Plug className="h-5 w-5" />, accent: "bg-emerald-500/10 text-emerald-300" },
  { name: "SendGrid", provider: "twilio.com", category: "Notify",
    description: "Email digests of low-confidence conversations to a list of reviewers. Daily, weekly, or threshold-triggered.",
    status: "available", icon: <Mail className="h-5 w-5" />, accent: "bg-sky-500/10 text-sky-300" },
  { name: "OpenAI", provider: "openai.com", category: "Routing",
    description: "Add OpenAI as a fallback provider. Bring-your-own-key reduces blended cost for non-sensitive prompts.",
    status: "connected", icon: <Plug className="h-5 w-5" />, accent: "bg-emerald-500/10 text-emerald-300",
    meta: "26.8% of traffic · BYO key" },
  { name: "AWS Bedrock", provider: "aws.amazon.com", category: "Routing",
    description: "Route to Bedrock-hosted Claude with VPC peering. Maintains data-residency in your AWS account.",
    status: "available", icon: <Plug className="h-5 w-5" />, accent: "bg-amber-500/10 text-amber-300" },
  { name: "Datadog", provider: "datadoghq.com", category: "Telemetry",
    description: "Forward conversation traces + cost events. Pre-built GroundTruth dashboard available in the marketplace.",
    status: "connected", icon: <Plug className="h-5 w-5" />, accent: "bg-violet-500/10 text-violet-300",
    meta: "trace.span × 18.4M / 7d" },
  { name: "S3 / R2", provider: "aws / cloudflare", category: "Source",
    description: "Sync a prefix as documents. Recurring crawl on a cron schedule with content-hash dedupe.",
    status: "available", icon: <Database className="h-5 w-5" />, accent: "bg-amber-500/10 text-amber-300" },
  { name: "Custom webhook", provider: "your endpoint", category: "Notify",
    description: "Fire a signed webhook on conversation_started, conversation_resolved, low_confidence, or escalation events.",
    status: "connected", icon: <Webhook className="h-5 w-5" />, accent: "bg-rose-500/10 text-rose-300",
    meta: "5 endpoints active" },
];

const CATEGORIES = ["All", "Routing", "Identity", "CRM", "Help desk", "Notify", "Source", "Telemetry"] as const;

export default function IntegrationsPage() {
  const counts = {
    connected: INTEGRATIONS.filter((i) => i.status === "connected").length,
    available: INTEGRATIONS.filter((i) => i.status === "available").length,
    beta: INTEGRATIONS.filter((i) => i.status === "beta").length,
  };

  return (
    <div className="px-6 py-6 max-w-6xl mx-auto space-y-6 animate-slide-up">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Integrations</h1>
          <p className="text-sm text-subtle mt-1">
            Connect GroundTruth to the rest of your stack — auth, CRM, help-desk, source, observability.
            <span className="ml-2 inline-flex gap-3 text-2xs">
              <span><span className="font-medium text-emerald-400">{counts.connected}</span> connected</span>
              <span><span className="font-medium text-zinc-200">{counts.available}</span> available</span>
              <span><span className="font-medium text-violet-300">{counts.beta}</span> in beta</span>
            </span>
          </p>
        </div>
        <button className="inline-flex items-center gap-1.5 rounded-md bg-zinc-50 text-zinc-950 px-3 py-1.5 text-sm font-medium hover:bg-white">
          Browse marketplace
          <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        {CATEGORIES.map((cat, i) => (
          <button
            key={cat}
            className={`rounded-full border px-3 py-1 text-xs ${
              i === 0
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 font-medium"
                : "border-white/[0.06] bg-surface/60 text-zinc-300 hover:bg-white/[0.04]"
            }`}
          >
            {cat}
            {cat === "All" ? ` · ${INTEGRATIONS.length}` : null}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {INTEGRATIONS.map((i) => (
          <Card key={i.name} className="card-lift" hoverable>
            <div className="px-5 pt-5 pb-4">
              <div className="flex items-start gap-3">
                <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${i.accent} flex-shrink-0`}>
                  {i.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold text-zinc-100 truncate">{i.name}</div>
                    {i.status === "connected" ? (
                      <Badge variant="success" dot>connected</Badge>
                    ) : i.status === "beta" ? (
                      <Badge variant="violet" dot>beta</Badge>
                    ) : (
                      <Badge variant="neutral">install</Badge>
                    )}
                  </div>
                  <div className="text-2xs text-subtle font-mono mt-0.5">{i.provider} · {i.category}</div>
                </div>
              </div>
              <p className="mt-3 text-xs text-zinc-400 leading-relaxed">{i.description}</p>
              {i.meta ? (
                <div className="mt-3 pt-3 border-t border-white/[0.04] flex items-center justify-between text-2xs">
                  <span className="text-subtle">{i.meta}</span>
                  <a className="inline-flex items-center gap-1 text-zinc-300 hover:text-zinc-100">
                    Configure <ArrowUpRight className="h-3 w-3" />
                  </a>
                </div>
              ) : (
                <div className="mt-3 pt-3 border-t border-white/[0.04] flex items-center justify-end text-2xs">
                  <a className="inline-flex items-center gap-1 text-emerald-300 hover:text-emerald-200">
                    Install <ArrowUpRight className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
