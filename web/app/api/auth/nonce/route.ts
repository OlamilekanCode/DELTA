import { backendUrl, isBackendConfigured } from "@/lib/bff";

export async function POST() {
  if (!isBackendConfigured()) {
    return Response.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const res = await fetch(backendUrl("/api/v1/auth/nonce"), { method: "POST", cache: "no-store" });
  const body = await res.json().catch(() => ({}));
  return Response.json(body, { status: res.status });
}
