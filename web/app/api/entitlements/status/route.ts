import { proxyToBackend } from "@/lib/bff";

export async function GET() {
  return proxyToBackend("/api/v1/entitlements/status", { requireAuth: true });
}
