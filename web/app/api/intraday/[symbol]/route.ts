import { proxyToBackend } from "@/lib/bff";

// Forwards the session token when present (for holder-tier stocks) but does
// not require one — free-tier live scores stay public. Polled client-side so
// the browser never needs the raw session token.
export async function GET(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  return proxyToBackend(`/api/v1/intraday/${encodeURIComponent(symbol)}`);
}
