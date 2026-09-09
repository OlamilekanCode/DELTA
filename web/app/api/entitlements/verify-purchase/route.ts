import { proxyToBackend } from "@/lib/bff";

export async function POST(request: Request) {
  const payload = await request.json().catch(() => null);
  const txHash = typeof payload?.tx_hash === "string" ? payload.tx_hash : null;
  if (!txHash) {
    return Response.json({ status: "invalid", message: "Missing transaction hash" }, { status: 400 });
  }

  return proxyToBackend("/api/v1/entitlements/verify-purchase", {
    requireAuth: true,
    method: "POST",
    body: { tx_hash: txHash },
  });
}
