import { nvdaChartData } from "@/lib/fixtures/nvda-chart";
import { topExposureScores } from "@/lib/fixtures/exposure-scores";
import { fetchCorrelation } from "@/lib/api";
import type { ExposureScore, PricePoint } from "@/lib/types";
import NVDAExampleClient from "./NVDAExampleClient";

type ApiScore = {
  symbol: string;
  name: string;
  category: string;
  score: number;
  raw_correlation: number;
  observations: number;
};

type ApiSeriesPoint = { date: string; value: number };

type ApiResponse = {
  scores: ApiScore[];
  price_series: {
    stock: ApiSeriesPoint[];
    crypto: Record<string, ApiSeriesPoint[]>;
  };
  demo: boolean;
};

export default async function NVDAExampleSection() {
  let scores: ExposureScore[] = topExposureScores;
  let chartData: PricePoint[] = nvdaChartData;
  let isDemo = true;

  try {
    const apiData = (await fetchCorrelation("NVDA")) as ApiResponse;

    scores = apiData.scores.map((s) => ({
      symbol: s.symbol,
      name: s.name,
      category: s.category,
      score: s.score,
      rawCorrelation: s.raw_correlation,
      observations: s.observations,
    }));

    const ps = apiData.price_series;
    const btcByDate = Object.fromEntries(
      (ps.crypto["BTC"] ?? []).map((p) => [p.date, p.value])
    );
    const ethByDate = Object.fromEntries(
      (ps.crypto["ETH"] ?? []).map((p) => [p.date, p.value])
    );

    chartData = ps.stock.map((p) => ({
      date: p.date,
      nvda: p.value,
      btc: btcByDate[p.date] ?? p.value,
      eth: ethByDate[p.date] ?? p.value,
    }));

    isDemo = apiData.demo;
  } catch {
    // API unavailable — silently fall back to fixture data
  }

  return <NVDAExampleClient scores={scores} chartData={chartData} isDemo={isDemo} />;
}
