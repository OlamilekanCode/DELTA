"use client";

import { useEffect, useRef } from "react";
import { nvdaChartData } from "@/lib/fixtures/nvda-chart";

export default function NVDAChart() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    let cleanup: (() => void) | null = null;

    import("lightweight-charts").then(({ createChart, LineSeries }) => {
      if (!containerRef.current) return;

      const chart = createChart(containerRef.current, {
        autoSize: true,
        layout: {
          background: { color: "transparent" },
          textColor: "#8E94A7",
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.04)" },
          horzLines: { color: "rgba(255,255,255,0.04)" },
        },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.09)" },
        timeScale: { borderColor: "rgba(255,255,255,0.09)", timeVisible: true },
        crosshair: { mode: 1 },
        handleScale: true,
        handleScroll: true,
      });

      cleanup = () => chart.remove();

      const nvdaSeries = chart.addSeries(LineSeries, { color: "#6D4AFF", lineWidth: 2, title: "NVDA" });
      const btcSeries  = chart.addSeries(LineSeries, { color: "#F7931A", lineWidth: 2, title: "BTC" });
      const ethSeries  = chart.addSeries(LineSeries, { color: "#3D7BFF", lineWidth: 2, title: "ETH" });

      type ChartTime = import("lightweight-charts").Time;
      const t = (d: string) => d as ChartTime;

      nvdaSeries.setData(nvdaChartData.map((p) => ({ time: t(p.date), value: p.nvda })));
      btcSeries.setData(nvdaChartData.map((p) => ({ time: t(p.date), value: p.btc })));
      ethSeries.setData(nvdaChartData.map((p) => ({ time: t(p.date), value: p.eth })));

      chart.timeScale().fitContent();
    });

    return () => { cleanup?.(); };
  }, []);

  return <div ref={containerRef} className="h-full w-full" />;
}
