"use client";

import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  BackgroundVariant,
  useNodesState,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { ApiGraphResult, ApiGraphNode } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  "Layer 1": "#F4C95D", "Layer 2": "#3D7BFF", "DeFi": "#9B7BFF",
  "Oracle/Data": "#38BDF8", "AI/Compute": "#71F79F", "Storage": "#FB923C",
  "Memecoin": "#F472B6", "Technology": "#9B7BFF", "Finance": "#2DD4BF",
};

function CenterNode({ data }: NodeProps) {
  return (
    <div
      className="flex h-16 w-16 flex-col items-center justify-center rounded-full border-2 border-violet/70 bg-panel2 text-center shadow-lg"
      style={{ boxShadow: "0 0 24px rgba(109,74,255,0.4)" }}
    >
      <span className="font-mono text-sm font-bold text-violet-light">{data.symbol as string}</span>
    </div>
  );
}

function CryptoNode({ data }: NodeProps) {
  const color = CATEGORY_COLORS[data.category as string] ?? "#9B7BFF";
  const score = data.score as number | null;
  return (
    <div
      className="flex h-12 w-20 flex-col items-center justify-center rounded-xl border text-center transition-shadow hover:shadow-lg"
      style={{
        borderColor: `${color}50`,
        background: `${color}12`,
        boxShadow: `0 0 8px ${color}20`,
      }}
    >
      <span className="font-mono text-xs font-bold" style={{ color }}>{data.symbol as string}</span>
      {score != null && (
        <span className="font-mono text-[9px] opacity-70" style={{ color }}>{score.toFixed(2)}</span>
      )}
    </div>
  );
}

const nodeTypes = { center: CenterNode, crypto: CryptoNode };

function buildLayout(apiNodes: ApiGraphNode[]): Node[] {
  const center = apiNodes.find((n) => n.is_center);
  const cryptos = apiNodes.filter((n) => !n.is_center);
  const cx = 300, cy = 250, radius = 200;
  const result: Node[] = [];

  if (center) {
    result.push({
      id: center.id,
      type: "center",
      position: { x: cx - 32, y: cy - 32 },
      data: { ...center } as Record<string, unknown>,
      draggable: true,
    });
  }

  cryptos.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / cryptos.length - Math.PI / 2;
    result.push({
      id: node.id,
      type: "crypto",
      position: {
        x: cx + radius * Math.cos(angle) - 40,
        y: cy + radius * Math.sin(angle) - 24,
      },
      data: { ...node } as Record<string, unknown>,
      draggable: true,
    });
  });

  return result;
}

function buildEdges(apiEdges: ApiGraphResult["edges"], minScore: number): Edge[] {
  return apiEdges
    .filter((e) => e.weight >= minScore)
    .map((e) => ({
      id: `${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      animated: false,
      style: {
        stroke: `rgba(155,123,255,${Math.min(0.8, e.weight)})`,
        strokeWidth: Math.max(1, e.weight * 4),
      },
      label: e.weight.toFixed(2),
      labelStyle: { fill: "#6B7280", fontSize: 10, fontFamily: "monospace" },
      labelBgStyle: { fill: "transparent" },
    }));
}

function GraphInner({ graphData }: { graphData: ApiGraphResult }) {
  const [minScore, setMinScore] = useState(0);
  const { fitView } = useReactFlow();

  const initialNodes = useMemo(() => buildLayout(graphData.nodes), [graphData.nodes]);
  const [allNodes, , onNodesChange] = useNodesState(initialNodes);

  // Recompute visible edges whenever the slider moves
  const visibleEdges = useMemo(
    () => buildEdges(graphData.edges, minScore),
    [graphData.edges, minScore],
  );

  // Derive connected node IDs from the visible edges, then filter nodes
  const connectedNodeIds = useMemo(
    () => new Set(visibleEdges.flatMap((e) => [e.source, e.target])),
    [visibleEdges],
  );

  const visibleNodes = useMemo(
    () => allNodes.filter((n) => {
      const d = n.data as { is_center?: boolean };
      return Boolean(d.is_center) || connectedNodeIds.has(n.id);
    }),
    [allNodes, connectedNodeIds],
  );

  const onReset = useCallback(() => { fitView({ padding: 0.15 }); }, [fitView]);

  return (
    <div className="relative h-full w-full">
      <div className="absolute left-4 top-4 z-10 flex flex-col gap-3">
        <div className="rounded-xl border border-white/[0.09] bg-panel/90 p-3 backdrop-blur-sm">
          <label className="mb-1 block font-mono text-[10px] text-muted">
            Min score: {minScore.toFixed(2)}
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-32 accent-violet"
          />
        </div>
        <button
          onClick={onReset}
          className="rounded-lg border border-white/[0.09] bg-panel/90 px-3 py-1.5 font-mono text-xs text-muted backdrop-blur-sm transition-colors hover:border-violet/30 hover:text-text"
        >
          Reset view
        </button>
      </div>

      <ReactFlow
        nodes={visibleNodes}
        edges={visibleEdges}
        onNodesChange={onNodesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.3}
        maxZoom={3}
        style={{ background: "transparent" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="rgba(255,255,255,0.06)"
        />
        <Controls
          style={{ background: "rgba(15,12,30,0.8)", border: "1px solid rgba(255,255,255,0.09)" }}
          showInteractive={false}
        />
      </ReactFlow>
    </div>
  );
}

interface Props {
  graphData: ApiGraphResult | null;
}

export default function ExposureGraphCanvas({ graphData }: Props) {
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="font-mono text-sm text-muted">No graph data available.</p>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <GraphInner graphData={graphData} />
    </ReactFlowProvider>
  );
}
