import { proxyToBackend } from "@/lib/bff";

export async function POST() {
  return proxyToBackend("/api/v1/portfolio/refresh", { requireAuth: true, method: "POST" });
}
