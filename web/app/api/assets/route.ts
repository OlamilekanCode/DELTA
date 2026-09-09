import { proxyToBackend } from "@/lib/bff";

// Forwards the session token when present so an authenticated holder sees
// the full catalogue — does not require one, since the free-tier list
// stays public. Client-fetched so components can refetch after sign-in
// without a full page reload (see PortfolioExposure.tsx's stock selector).
export async function GET(request: Request) {
  const url = new URL(request.url);
  const search = url.searchParams.toString();
  return proxyToBackend(`/api/v1/assets${search ? `?${search}` : ""}`);
}
