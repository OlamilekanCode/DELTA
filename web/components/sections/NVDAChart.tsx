"use client";

import { useEffect, useRef } from "react";
import { nvdaChartData } from "@/lib/fixtures/nvda-chart";

export default function NVDAChart() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    let chart: { remove: () => void } | null = null;

    import("lightweight-charts").then(({ createChart, LineStyle }) => {
      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: {
          background: { color: "transparent" },
          textColor: "#8E94A7",
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.04)" },
          horzLines: { color: "rgba(255,255,255,0.04)" },
        },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.09)" },
        timeScale: {
          borderColor: "rgba(255,255,255,0.09)",
          timeVisible: true,
        },
        crosshair: { mode: 1 },
        handleScale: true,
        handleScroll: true,
      });

      const nvdaSeries = chart.addLineSeries({
        color: "#6D4AFF",
        lineWidth: 2,
        title: "NVDA",
        lineStyle: LineStyle.Solid,
      });

      const btcSeries = chart.addLineSeries({
        color: "#F7931A",
        lineWidth: 2,
        title: "BTC",
        lineStyle: LineStyle.Solid,
      });

      const ethSeries = chart.addLineSeries({
        color: "#3D7BFF",
        lineWidth: 2,
        title: "ETH",
        lineStyle: LineStyle.Solid,
      });

      const toChartTime = (d: string) => d as unknown as import("lightweight-charts").Time;

      nvdaSeries.setData(nvdaChartData.map((p) => ({ time: toChartTime(p.date), value: p.nvda })));
      btcSeries.setData(nvdaChartData.map((p) => ({ time: toChartTime(p.date), value: p.btc })));
      ethSeries.setData(nvdaChartData.map((p) => ({ time: toChartTime(p.date), value: p.eth })));

      chart.timeScale().fitContent();
    });

    return () => { chart?.remove(); };
  }, []);

  return <div ref={containerRef} className="h-full w-full" />;
}
