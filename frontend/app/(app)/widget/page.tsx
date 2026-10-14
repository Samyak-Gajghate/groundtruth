"use client";

import { useEffect, useState } from "react";
import { Copy, Check, Shield, Code2, Globe, Sparkles } from "lucide-react";
import { api, API_BASE, type Me } from "@/lib/api";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function WidgetPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { api.me().then(setMe).catch(() => {}); }, []);
  if (!me) return <div className="p-6 text-subtle text-sm">Loading…</div>;

  const widgetUrl = `${API_BASE.replace(/\/$/, "")}/static/widget.js`;
  // Branded URLs shown in the snippet. The widget still calls the configured
  // API_BASE at runtime; only the displayed copy uses the customer-facing host.
  const brandHost = `${me.tenant_slug}.groundtruth.ai`;
  const displayWidgetUrl = `https://${brandHost}/widget.js`;
  const displayApiUrl = `https://api.${brandHost}`;
  const embed = `<script\n  src="${displayWidgetUrl}"\n  data-public-key="${me.tenant_public_key}"\n  data-api="${displayApiUrl}"\n></script>`;

  function copy() {
    navigator.clipboard.writeText(embed.replace(/\n  /g, " ").replace(/\n/g, ""));
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="px-6 py-6 max-w-7xl mx-auto space-y-6 animate-slide-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Embed widget</h1>
        <p className="text-sm text-subtle mt-1">
          Drop a 4-line snippet on any page. The widget answers from <span className="text-zinc-200">your</span> indexed docs only.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 space-y-4">
          <Card>
            <CardHeader
              title="Installation"
              subtitle="Paste before </body>. The widget self-mounts."
              action={
                <button onClick={copy} className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.06] bg-white/[0.04] px-2.5 py-1 text-xs text-zinc-200 hover:bg-white/[0.06]">
                  {copied ? <><Check className="h-3 w-3 text-emerald-400" /> Copied</> : <><Copy className="h-3 w-3" /> Copy</>}
                </button>
              }
            />
            <CardBody>
              <pre className="rounded-lg border border-white/[0.06] bg-bg/60 p-4 text-xs overflow-x-auto font-mono leading-6">
                <code className="text-zinc-300">
                  <span className="text-violet-300">&lt;script</span>{"\n"}
                  {"  "}<span className="text-emerald-300">src</span>=<span className="text-amber-300">"{displayWidgetUrl}"</span>{"\n"}
                  {"  "}<span className="text-emerald-300">data-public-key</span>=<span className="text-amber-300">"{me.tenant_public_key}"</span>{"\n"}
                  {"  "}<span className="text-emerald-300">data-api</span>=<span className="text-amber-300">"{displayApiUrl}"</span>{"\n"}
                  <span className="text-violet-300">&gt;&lt;/script&gt;</span>
                </code>
              </pre>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Public key" subtitle="Safe to ship to the browser — read-only widget scope." />
            <CardBody className="space-y-2">
              <div className="flex items-center gap-2 rounded-md border border-white/[0.06] bg-bg/60 px-3 py-2 font-mono text-sm">
                <span className="text-emerald-300">{me.tenant_public_key}</span>
              </div>
              <div className="flex items-center gap-2 text-2xs text-subtle">
                <Shield className="h-3 w-3 text-emerald-400" />
                Scoped to <code className="text-zinc-300">/widget/chat</code> only. Never grants admin access.
              </div>
            </CardBody>
          </Card>

          <div className="grid grid-cols-3 gap-3">
            <FeatureCard icon={<Globe className="h-4 w-4 text-emerald-400" />} title="Any framework" body="Works on React, Next, Vue, plain HTML, Webflow." />
            <FeatureCard icon={<Sparkles className="h-4 w-4 text-violet-400" />} title="Citation-grounded" body="Every answer links the source doc and chunk." />
            <FeatureCard icon={<Code2 className="h-4 w-4 text-sky-400" />} title="2 KB gzipped" body="Vanilla JS, no React, no build step required." />
          </div>
        </div>

        <div className="lg:col-span-2">
          <Card className="overflow-hidden h-[600px]">
            <CardHeader
              title="Live preview"
              subtitle="Click the bubble to talk to your assistant"
              action={<Badge variant="success" dot>connected</Badge>}
            />
            <iframe
              srcDoc={`<!doctype html><html><body style="margin:0;height:100vh;background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);color:#fff;font-family:Inter,system-ui;display:flex;align-items:center;justify-content:center;">
<div style="text-align:center;padding:24px;max-width:300px;">
  <div style="font-size:11px;letter-spacing:0.1em;color:#a78bfa;text-transform:uppercase;margin-bottom:8px;">acme.example</div>
  <h2 style="margin:0 0 8px;font-size:18px;">Acme Robotics</h2>
  <p style="margin:0;font-size:13px;color:#cbd5e1;line-height:1.5;">Demo host page. Tap the chat bubble in the bottom-right to ask anything about your robot.</p>
</div>
<script src="${widgetUrl}" data-public-key="${me.tenant_public_key}" data-api="${API_BASE}"></script>
</body></html>`}
              className="w-full h-[calc(100%-58px)] border-t border-white/[0.06]"
            />
          </Card>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface/60 p-4">
      <div className="flex items-center gap-2 mb-1.5">{icon}<span className="text-sm font-medium text-zinc-100">{title}</span></div>
      <p className="text-2xs text-subtle leading-relaxed">{body}</p>
    </div>
  );
}
