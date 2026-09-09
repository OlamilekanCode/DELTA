import { proxyToBackend } from "@/lib/bff";

// Forwards the session token when present (for holder-tier stocks) but does
// not require one — free-tier graph data stays public. Client-fetched so the
// Live/Historical toggle can refetch without a full page reload.
export async function GET(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const url = new URL(request.url);
  const search = url.searchParams.toString();
  return proxyToBackend(`/api/v1/graphs/${encodeURIComponent(symbol)}${search ? `?${search}` : ""}`);
}
