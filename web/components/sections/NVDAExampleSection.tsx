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
    const stockByDate = Object.fromEntries(ps.stock.map((p) => [p.date, p.value]));
    const btcByDate = Object.fromEntries(
      (ps.crypto["BTC"] ?? []).map((p) => [p.date, p.value])
    );
    const ethByDate = Object.fromEntries(
      (ps.crypto["ETH"] ?? []).map((p) => [p.date, p.value])
    );

    // Inner-join: only render dates where all three series have a value.
    // Never substitute NVDA's price for missing BTC or ETH data.
    const commonDates = ps.stock
      .map((p) => p.date)
      .filter((d) => btcByDate[d] !== undefined && ethByDate[d] !== undefined);

    chartData = commonDates.map((d) => ({
      date: d,
      nvda: stockByDate[d],
      btc: btcByDate[d],
      eth: ethByDate[d],
    }));

    isDemo = apiData.demo;
  } catch {
    // API unavailable — silently fall back to fixture data
  }

  return <NVDAExampleClient scores={scores} chartData={chartData} isDemo={isDemo} />;
}
