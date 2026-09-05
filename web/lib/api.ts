const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function fetchCorrelation(symbol: string, days = 90): Promise<unknown> {
  const res = await fetch(`${BASE}/api/v1/correlation/${symbol}?days=${days}`, {
    next: { revalidate: 3600 },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function fetchAssets(type?: "crypto" | "stock"): Promise<unknown> {
  const url = type ? `${BASE}/api/v1/assets?type=${type}` : `${BASE}/api/v1/assets`;
  const res = await fetch(url, { next: { revalidate: 86400 } });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
