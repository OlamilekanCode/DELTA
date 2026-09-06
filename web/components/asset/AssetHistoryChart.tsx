"use client";

import { useEffect, useRef } from "react";
import type { IChartApi } from "lightweight-charts";
import type { ApiHistoryPoint } from "@/lib/types";

interface Props {
  prices: ApiHistoryPoint[];
  color?: string;
  label?: string;
}

export default function AssetHistoryChart({ prices, color = "#9B7BFF", label }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || prices.length === 0) return;

    let chart: IChartApi | null = null;
    let observer: ResizeObserver | null = null;

    import("lightweight-charts").then(({ createChart, ColorType, LineSeries }) => {
      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#6B7280" },
        grid: { vertLines: { color: "rgba(255,255,255,0.05)" }, horzLines: { color: "rgba(255,255,255,0.05)" } },
        crosshair: { vertLine: { color: "rgba(155,123,255,0.5)" }, horzLine: { color: "rgba(155,123,255,0.5)" } },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
        timeScale: { borderColor: "rgba(255,255,255,0.1)", timeVisible: true },
        handleScroll: true,
        handleScale: true,
      });

      const series = chart.addSeries(LineSeries, {
        color,
        lineWidth: 2,
        crosshairMarkerVisible: true,
        lastValueVisible: true,
        priceLineVisible: false,
      });

      const data = prices.map((p) => ({
        time: p.date as `${number}-${number}-${number}`,
        value: p.close,
      }));
      series.setData(data);
      chart.timeScale().fitContent();

      observer = new ResizeObserver(() => {
        if (containerRef.current && chart) {
          chart.applyOptions({
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight,
          });
        }
      });
      observer.observe(containerRef.current);
    });

    return () => {
      observer?.disconnect();
      chart?.remove();
    };
  }, [prices, color]);

  if (prices.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="font-mono text-sm text-muted">No price history available.</p>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      {label && (
        <p className="absolute left-0 top-0 z-10 font-mono text-xs text-muted">{label}</p>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
