"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sparkles, Loader2 } from "lucide-react";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const r = await api.login({ email, password });
      setToken(r.access_token);
      router.push("/dashboard");
      router.refresh();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex flex-1 items-center justify-center relative overflow-hidden border-r border-white/[0.06]">
        <div className="absolute inset-0 bg-gradient-to-br from-violet-500/10 via-transparent to-emerald-500/10" />
        <div className="relative max-w-md px-12">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-emerald-500 shadow-glow mb-6">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <h2 className="text-3xl font-semibold tracking-tight leading-tight">
            AI customer support, <span className="text-emerald-400">grounded</span> in your docs.
          </h2>
          <p className="text-zinc-400 mt-4 leading-relaxed">
            Multi-tenant retrieval with citation-grounded answers, an embeddable widget, and per-customer cost reporting. Built for B2B SaaS.
          </p>
          <ul className="mt-8 space-y-2 text-sm text-zinc-300">
            <li className="flex items-center gap-2"><span className="h-1 w-1 rounded-full bg-emerald-400" /> Row-level tenant isolation</li>
            <li className="flex items-center gap-2"><span className="h-1 w-1 rounded-full bg-emerald-400" /> Streaming answers with inline citations</li>
            <li className="flex items-center gap-2"><span className="h-1 w-1 rounded-full bg-emerald-400" /> 2 KB embeddable widget</li>
            <li className="flex items-center gap-2"><span className="h-1 w-1 rounded-full bg-emerald-400" /> Mock + Stripe billing adapters</li>
          </ul>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="text-sm text-subtle mt-1 mb-6">Log in to your workspace</p>
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="text-xs text-subtle">Email</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="mt-1 w-full rounded-md bg-surface/60 border border-white/[0.06] px-3 py-2 text-sm placeholder:text-subtle focus:outline-none focus:border-white/20"
                autoFocus
              />
            </div>
            <div>
              <label className="text-xs text-subtle">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1 w-full rounded-md bg-surface/60 border border-white/[0.06] px-3 py-2 text-sm placeholder:text-subtle focus:outline-none focus:border-white/20"
              />
            </div>
            <button
              disabled={busy || !email || !password}
              className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-zinc-50 text-zinc-950 font-medium py-2 text-sm disabled:opacity-40 hover:bg-white"
            >
              {busy ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Signing in…</> : "Continue"}
            </button>
          </form>
          {err ? <div className="rounded-md border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-300 mt-3">{err}</div> : null}
          <div className="text-sm mt-4 text-subtle">
            New here? <Link href="/signup" className="text-zinc-100 hover:underline">Create an account</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
