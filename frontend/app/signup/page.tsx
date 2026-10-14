"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, setToken } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await api.signup({ email, password, tenant_name: tenantName });
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
    <div className="max-w-sm mx-auto p-6 flex-1 flex flex-col justify-center">
      <h1 className="text-xl font-semibold mb-4">Create your workspace</h1>
      <form onSubmit={submit} className="space-y-3">
        <input value={tenantName} onChange={(e) => setTenantName(e.target.value)} placeholder="Workspace name (e.g. Acme Robotics)" className="w-full rounded bg-neutral-900 border border-neutral-700 px-3 py-2 text-sm" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin email" className="w-full rounded bg-neutral-900 border border-neutral-700 px-3 py-2 text-sm" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password (min 8 chars)" className="w-full rounded bg-neutral-900 border border-neutral-700 px-3 py-2 text-sm" />
        <button disabled={busy || !email || !password || !tenantName} className="w-full rounded bg-sky-500 text-neutral-950 font-medium py-2 disabled:opacity-40">{busy ? "Creating…" : "Sign up"}</button>
      </form>
      {err ? <div className="text-red-300 text-sm mt-3">{err}</div> : null}
      <div className="text-sm mt-4 text-neutral-400">
        Already have one? <Link href="/login" className="text-sky-400 hover:underline">Log in</Link>
      </div>
    </div>
  );
}
