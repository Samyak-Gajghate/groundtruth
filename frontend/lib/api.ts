export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const TOKEN_KEY = "saas_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null): void {
  if (typeof window === "undefined") return;
  if (t) window.localStorage.setItem(TOKEN_KEY, t);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { ...(init.headers as Record<string, string> | undefined) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(init.body instanceof FormData) && init.body) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }
  const r = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export type Me = {
  user_id: string;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  tenant_public_key: string;
  plan: string;
  email: string;
  is_admin: boolean;
};

export const api = {
  signup: (body: { email: string; password: string; tenant_name: string }) =>
    req<{ access_token: string }>("/auth/signup", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    req<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => req<Me>("/auth/me"),

  listDocs: () =>
    req<Array<{ id: string; filename: string; byte_size: number; page_count: number | null; chunk_count: number; created_at: string }>>(
      "/documents",
    ),
  uploadDoc: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ id: string }>("/documents", { method: "POST", body: fd });
  },
  deleteDoc: (id: string) => req<void>(`/documents/${id}`, { method: "DELETE" }),

  listConversations: () =>
    req<Array<{ id: string; channel: string; end_user_session: string; created_at: string; last_message_preview: string | null; message_count: number }>>(
      "/chat/conversations",
    ),
  getConversation: (id: string) =>
    req<{ id: string; messages: Array<{ id: string; role: string; content: string; citations: { items?: Array<{ marker: string; filename: string; snippet: string }> }; created_at: string }> }>(
      `/chat/conversations/${id}`,
    ),

  billingMe: () =>
    req<{
      plan: string;
      status: string;
      limits: { docs: number; messages: number };
      used_messages_this_month: number;
      cost_usd_this_month: number;
    }>("/billing/me"),
  plans: () => req<{ plans: Array<{ id: string; docs: number; messages: number }> }>("/billing/plans"),
  checkout: (plan: string, returnUrl: string) =>
    req<{ url: string; session_id: string; provider: string }>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan, return_url: returnUrl }),
    }),
  mockConfirm: (session_id: string) =>
    req<{ ok: boolean; plan: string }>("/billing/mock/confirm", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  overview: () =>
    req<{
      totals: { documents: number; conversations: number; messages: number; cost_usd_this_month: number };
      daily: Array<{ day: string; cost_usd: number; tokens: number }>;
    }>("/admin/overview"),
};
