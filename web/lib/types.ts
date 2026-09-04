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
