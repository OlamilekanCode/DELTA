import { cookies } from "next/headers";

/**
 * BFF pattern: browser -> these Next.js route handlers (same origin, HttpOnly
 * cookie) -> Render API (Authorization header). The session token itself is
 * never exposed to client-side JS or stored in localStorage.
 */

export const SESSION_COOKIE_NAME = "synthex_session";
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

// Server-only — never NEXT_PUBLIC_. Must be the backend's public HTTPS
// origin (Vercel cannot reach a Render private/internal URL).
const BACKEND_URL = (process.env.BACKEND_API_URL ?? "").replace(/\/$/, "");

export async function getSessionToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE_NAME)?.value ?? null;
}

/**
 * Proxy a request to the backend, forwarding the session token (if any) as a
 * Bearer header. `requireAuth: true` returns 401 locally without touching
 * the backend when there's no session. Every proxied response is `no-store`
 * — this path only ever serves authenticated or entitlement-specific data,
 * which must never be cached or shared between users.
 */
export async function proxyToBackend(
  path: string,
  options: { requireAuth?: boolean; method?: "GET" | "POST"; body?: unknown } = {}
): Promise<Response> {
  if (!BACKEND_URL) {
    return Response.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const token = await getSessionToken();
  if (options.requireAuth && !token) {
    return Response.json({ error: "unauthenticated" }, { status: 401 });
  }

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });
  const body = await res.json().catch(() => ({}));
  return Response.json(body, { status: res.status });
}

export function backendUrl(path: string): string {
  return `${BACKEND_URL}${path}`;
}

export function isBackendConfigured(): boolean {
  return Boolean(BACKEND_URL);
}
