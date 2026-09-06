"use client";

import dynamic from "next/dynamic";
import type { ApiHistoryPoint } from "@/lib/types";

const Chart = dynamic(() => import("./AssetHistoryChart"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-xl bg-panel2" />,
});

interface Props {
  prices: ApiHistoryPoint[];
  color?: string;
  label?: string;
}

export default function AssetHistoryChartClient(props: Props) {
  return <Chart {...props} />;
}
