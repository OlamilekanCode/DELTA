// ── Legacy types (used by fixture data + hero graph) ────────────────────────

export interface GraphNode {
  id: string;
  symbol: string;
  name: string;
  category: string;
  score: number;
  price: string;
  x: number;
  y: number;
  isCenter?: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  weight: number;
}

export interface ExposureScore {
  symbol: string;
  name: string;
  category: string;
  score: number;
  rawCorrelation: number;
  observations: number;
}

export interface PricePoint {
  date: string;
  nvda: number;
  btc: number;
  eth: number;
}

// ── API response types ────────────────────────────────────────────────────────

export interface ApiAsset {
  symbol: string;
  name: string;
  category: string;
  asset_type: "stock" | "crypto";
  coingecko_id: string | null;
  last_price: number | null;
  last_price_date: string | null;
  is_demo: boolean | null;
  // Quote fields — populated for crypto assets only
  change_24h_pct: number | null;
  market_cap_usd: number | null;
  volume_24h_usd: number | null;
  quote_ts: string | null;
  quote_provider: string | null;
}

export interface ApiAssetListOut {
  assets: ApiAsset[];
}

export interface ApiHistoryPoint {
  date: string;
  close: number;
}

export interface ApiAssetHistoryOut {
  symbol: string;
  asset_type: "stock" | "crypto";
  prices: ApiHistoryPoint[];
  is_demo: boolean | null;
  provider: string;
}

export interface ApiExposureScore {
  symbol: string;
  name: string;
  category: string;
  score: number;
  raw_correlation: number;
  observations: number;
}

export interface ApiExposuresResult {
  stock: { symbol: string; name: string };
  scores: ApiExposureScore[];
  computed_at: string | null;
  stale: boolean;
  demo: boolean;
}

export interface ApiGraphNode {
  id: string;
  symbol: string;
  name: string;
  category: string;
  score: number | null;
  is_center: boolean;
}

export interface ApiGraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface ApiGraphResult {
  stock: { symbol: string; name: string };
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  demo: boolean;
  computed_at: string | null;
}
