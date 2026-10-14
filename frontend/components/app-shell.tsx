"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  FileText,
  MessagesSquare,
  CreditCard,
  Code2,
  Plug,
  LogOut,
  Sparkles,
  Search,
  Bell,
  ChevronsUpDown,
} from "lucide-react";
import { api, getToken, setToken, type Me } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/conversations", label: "Conversations", icon: MessagesSquare },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/widget", label: "Embed widget", icon: Code2 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const t = getToken();
    if (!t) { router.push("/login"); return; }
    api.me().then(setMe).catch((e) => setErr((e as Error).message));
  }, [router]);

  function logout() { setToken(null); router.push("/login"); }

  if (err) return <div className="p-6 text-rose-300">{err}</div>;
  if (!me) {
    return (
      <div className="flex h-screen items-center justify-center text-subtle text-sm gap-2">
        <Sparkles className="h-4 w-4 animate-pulse-dot" /> Loading…
      </div>
    );
  }

  const planVariant = me.plan === "pro" ? "success" : me.plan === "enterprise" ? "violet" : "neutral";
  const initials = (me.email || "?").slice(0, 2).toUpperCase();
  const currentLabel = NAV.find((n) => n.href === pathname)?.label || "Overview";

  return (
    <div className="flex min-h-screen">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-white/[0.06] bg-surface/40 backdrop-blur-xl">
        <div className="px-4 pt-5 pb-4 border-b border-white/[0.06]">
          <button className="group flex items-center gap-2 w-full rounded-lg px-2 py-1.5 hover:bg-white/[0.04]">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-violet-500 to-emerald-500 text-white">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="flex-1 text-left">
              <div className="text-sm font-medium leading-tight">{me.tenant_name}</div>
              <div className="text-2xs text-subtle leading-tight">{me.tenant_slug}.groundtruth.ai</div>
            </div>
            <ChevronsUpDown className="h-3.5 w-3.5 text-subtle" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5">
          <div className="px-2 pb-1 pt-2 text-2xs uppercase tracking-wider text-subtle">Workspace</div>
          {NAV.map((n) => {
            const Icon = n.icon;
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={clsx(
                  "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-white/[0.06] text-zinc-50"
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.03]",
                )}
              >
                <Icon className={clsx("h-4 w-4", active ? "text-zinc-100" : "text-zinc-500")} />
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/[0.06] p-3">
          <div className="flex items-center gap-2.5 rounded-lg p-2 hover:bg-white/[0.04]">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-fuchsia-600 text-2xs font-semibold text-white">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium truncate">{me.email}</div>
              <div className="text-2xs text-subtle">
                <Badge variant={planVariant} dot>{me.plan.toUpperCase()}</Badge>
              </div>
            </div>
            <button onClick={logout} title="Log out" className="text-subtle hover:text-zinc-100">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-white/[0.06] bg-bg/70 px-6 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-subtle">{me.tenant_name}</span>
            <span className="text-subtle/50">/</span>
            <span className="font-medium text-zinc-100">{currentLabel}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden md:flex items-center gap-2 rounded-md border border-white/[0.06] bg-surface/60 px-2.5 py-1.5 text-xs text-subtle min-w-[260px]">
              <Search className="h-3.5 w-3.5" />
              <span className="flex-1">Search docs, conversations…</span>
              <kbd className="hidden lg:inline-flex h-4 px-1 items-center rounded border border-white/10 bg-white/[0.04] text-[10px] text-subtle">⌘K</kbd>
            </div>
            <button className="rounded-md border border-white/[0.06] bg-surface/60 p-1.5 text-subtle hover:text-zinc-100">
              <Bell className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
