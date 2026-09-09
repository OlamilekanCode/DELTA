import { cookies } from "next/headers";
import {
  backendUrl,
  isBackendConfigured,
  realClientIp,
  SESSION_COOKIE_NAME,
  SESSION_MAX_AGE_SECONDS,
} from "@/lib/bff";

export async function POST(request: Request) {
  if (!isBackendConfigured()) {
    return Response.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const payload = await request.json().catch(() => null);
  if (!payload?.message || !payload?.signature) {
    return Response.json({ error: "invalid_request" }, { status: 400 });
  }

  const clientIp = realClientIp(request);
  const secret = process.env.BFF_SHARED_SECRET;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (clientIp && secret) {
    headers["X-Forwarded-Client-IP"] = clientIp;
    headers["X-BFF-Shared-Secret"] = secret;
  }

  const res = await fetch(backendUrl("/api/v1/auth/verify"), {
    method: "POST",
    headers,
    body: JSON.stringify({ message: payload.message, signature: payload.signature }),
    cache: "no-store",
  });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    return Response.json(body, { status: res.status });
  }

  const store = await cookies();
  store.set(SESSION_COOKIE_NAME, body.session_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: SESSION_MAX_AGE_SECONDS,
    path: "/",
  });

  return Response.json({ wallet_address: body.wallet_address, authenticated: true });
}
