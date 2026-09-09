"use client";

import dynamic from "next/dynamic";
import type { ApiGraphResult } from "@/lib/types";

const Canvas = dynamic(() => import("./ExposureGraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center">
      <p className="font-mono text-sm text-muted">Loading graph…</p>
    </div>
  ),
});

export default function ExposureGraphCanvasClient({ graphData }: { graphData: ApiGraphResult | null }) {
  return <Canvas graphData={graphData} />;
}
