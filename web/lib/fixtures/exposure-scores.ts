import type { ExposureScore } from "@/lib/types";

export const topExposureScores: ExposureScore[] = [
  { symbol: "BTC",  name: "Bitcoin",   category: "BTC Ecosystem", score: 0.78, rawCorrelation: 0.78, observations: 63 },
  { symbol: "ETH",  name: "Ethereum",  category: "DeFi",          score: 0.71, rawCorrelation: 0.71, observations: 63 },
  { symbol: "SOL",  name: "Solana",    category: "AI",            score: 0.65, rawCorrelation: 0.65, observations: 61 },
  { symbol: "AVAX", name: "Avalanche", category: "DeFi",          score: 0.58, rawCorrelation: 0.58, observations: 63 },
  { symbol: "LINK", name: "Chainlink", category: "AI",            score: 0.52, rawCorrelation: 0.52, observations: 62 },
];
