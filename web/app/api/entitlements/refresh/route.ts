import { proxyToBackend } from "@/lib/bff";

export async function POST() {
  return proxyToBackend("/api/v1/entitlements/refresh", { requireAuth: true, method: "POST" });
}
