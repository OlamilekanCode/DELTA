import { backendUrl, isBackendConfigured, realClientIp } from "@/lib/bff";

export async function POST(request: Request) {
  if (!isBackendConfigured()) {
    return Response.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const clientIp = realClientIp(request);
  const secret = process.env.BFF_SHARED_SECRET;
  const headers: Record<string, string> =
    clientIp && secret ? { "X-Forwarded-Client-IP": clientIp, "X-BFF-Shared-Secret": secret } : {};
  const res = await fetch(backendUrl("/api/v1/auth/nonce"), { method: "POST", headers, cache: "no-store" });
  const body = await res.json().catch(() => ({}));
  return Response.json(body, { status: res.status });
}
