import { proxyToBackend } from "@/lib/bff";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stock = searchParams.get("stock");
  const qs = stock ? `?stock=${encodeURIComponent(stock)}` : "";
  return proxyToBackend(`/api/v1/portfolio/exposure${qs}`, { requireAuth: true });
}
