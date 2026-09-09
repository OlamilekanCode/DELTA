import { proxyToBackend, realClientIp } from "@/lib/bff";

export async function POST(request: Request) {
  return proxyToBackend("/api/v1/entitlements/refresh", {
    requireAuth: true,
    method: "POST",
    clientIp: realClientIp(request),
  });
}
