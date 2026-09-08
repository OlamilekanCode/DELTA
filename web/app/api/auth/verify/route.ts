import { cookies } from "next/headers";
import { backendUrl, isBackendConfigured, SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS } from "@/lib/bff";

export async function POST(request: Request) {
  if (!isBackendConfigured()) {
    return Response.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const payload = await request.json().catch(() => null);
  if (!payload?.message || !payload?.signature) {
    return Response.json({ error: "invalid_request" }, { status: 400 });
  }

  const res = await fetch(backendUrl("/api/v1/auth/verify"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
