import type { GraphNode, GraphEdge } from "@/lib/types";

export const heroNodes: GraphNode[] = [
  { id: "nvda", symbol: "NVDA", name: "NVIDIA", category: "Semiconductors", score: 1, price: "—", x: 50, y: 50, isCenter: true },
  { id: "btc",  symbol: "BTC",  name: "Bitcoin",   category: "BTC Ecosystem", score: 0.78, price: "—", x: 50, y: 14 },
  { id: "eth",  symbol: "ETH",  name: "Ethereum",  category: "DeFi",          score: 0.71, price: "—", x: 78, y: 22 },
  { id: "sol",  symbol: "SOL",  name: "Solana",    category: "AI",            score: 0.65, price: "—", x: 90, y: 50 },
  { id: "avax", symbol: "AVAX", name: "Avalanche", category: "DeFi",          score: 0.58, price: "—", x: 78, y: 78 },
  { id: "link", symbol: "LINK", name: "Chainlink", category: "AI",            score: 0.52, price: "—", x: 50, y: 86 },
  { id: "rndr", symbol: "RNDR", name: "Render",    category: "AI",            score: 0.61, price: "—", x: 22, y: 78 },
  { id: "fet",  symbol: "FET",  name: "Fetch.ai",  category: "AI",            score: 0.56, price: "—", x: 10, y: 50 },
  { id: "arb",  symbol: "ARB",  name: "Arbitrum",  category: "DeFi",          score: 0.49, price: "—", x: 22, y: 22 },
];

export const heroEdges: GraphEdge[] = [
  { from: "nvda", to: "btc",  weight: 0.78 },
  { from: "nvda", to: "eth",  weight: 0.71 },
  { from: "nvda", to: "sol",  weight: 0.65 },
  { from: "nvda", to: "avax", weight: 0.58 },
  { from: "nvda", to: "link", weight: 0.52 },
  { from: "nvda", to: "rndr", weight: 0.61 },
  { from: "nvda", to: "fet",  weight: 0.56 },
  { from: "nvda", to: "arb",  weight: 0.49 },
];

export const previewNodes: GraphNode[] = [
  { id: "nvda", symbol: "NVDA", name: "NVIDIA",    category: "Semiconductors", score: 1,    price: "Demo data", x: 50, y: 50, isCenter: true },
  { id: "btc",  symbol: "BTC",  name: "Bitcoin",   category: "BTC Ecosystem",  score: 0.78, price: "Demo data", x: 50, y: 12 },
  { id: "eth",  symbol: "ETH",  name: "Ethereum",  category: "DeFi",           score: 0.71, price: "Demo data", x: 82, y: 25 },
  { id: "sol",  symbol: "SOL",  name: "Solana",    category: "AI",             score: 0.65, price: "Demo data", x: 88, y: 58 },
  { id: "avax", symbol: "AVAX", name: "Avalanche", category: "DeFi",           score: 0.58, price: "Demo data", x: 72, y: 85 },
  { id: "link", symbol: "LINK", name: "Chainlink", category: "AI",             score: 0.52, price: "Demo data", x: 40, y: 90 },
  { id: "rndr", symbol: "RNDR", name: "Render",    category: "AI",             score: 0.61, price: "Demo data", x: 14, y: 72 },
  { id: "fet",  symbol: "FET",  name: "Fetch.ai",  category: "AI",             score: 0.56, price: "Demo data", x: 10, y: 40 },
  { id: "arb",  symbol: "ARB",  name: "Arbitrum",  category: "DeFi",           score: 0.49, price: "Demo data", x: 26, y: 18 },
];
