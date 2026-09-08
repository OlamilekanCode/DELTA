import { proxyToBackend } from "@/lib/bff";

// Forwards the session token when present (for holder-tier assets) but does
// not require one — free-tier asset charts stay public. Used by client-side
// chart-range switching so the browser never needs the raw session token.
export async function GET(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const { searchParams } = new URL(request.url);
  const qs = searchParams.toString();
  return proxyToBackend(`/api/v1/assets/${encodeURIComponent(symbol)}/history${qs ? `?${qs}` : ""}`);
}
