import { proxyToBackend } from "@/lib/bff";

export async function GET() {
  return proxyToBackend("/api/v1/auth/session");
}
