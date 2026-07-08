'use client';

import dynamic from 'next/dynamic';
import { useCallback, useMemo } from 'react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import type { TaintGraph } from '@/lib/types';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => (
    <div className="flex h-96 items-center justify-center">
      <LoadingSpinner label="Loading graph..." />
    </div>
  ),
});

const NODE_COLORS: Record<string, string> = {
  source: '#ef4444',
  sink: '#f59e0b',
  transform: '#3b82f6',
  function: '#22c55e',
};

interface TaintGraphViewProps {
  graph: TaintGraph;
  height?: number;
}

export default function TaintGraphView({ graph, height = 480 }: TaintGraphViewProps) {
  const graphData = useMemo(() => {
    const links = graph.links || graph.edges || [];
    return {
      nodes: graph.nodes.map((n) => ({
        id: n.id,
        name: n.label || n.id,
        type: n.type,
      })),
      links: links.map((l) => ({
        source: l.source,
        target: l.target,
        label: l.label,
      })),
    };
  }, [graph]);

  const nodeCanvasObject = useCallback(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name as string;
      const fontSize = 12 / globalScale;
      const nodeRadius = 6;

      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = NODE_COLORS[node.type as string] || '#8b949e';
      ctx.fill();
      ctx.strokeStyle = '#2d333b';
      ctx.lineWidth = 1 / globalScale;
      ctx.stroke();

      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#e6edf3';
      ctx.fillText(label, node.x, node.y + nodeRadius + 2);
    },
    []
  );

  if (!graph.nodes.length) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-border bg-surface">
        <p className="text-sm text-muted">No taint graph data available</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-white">Taint Flow Graph</h3>
        <div className="flex items-center gap-4 text-xs text-muted">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <span key={type} className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
              {type}
            </span>
          ))}
        </div>
      </div>
      <div style={{ height }}>
        <ForceGraph2D
          graphData={graphData}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.beginPath();
            ctx.arc(node.x!, node.y!, 8, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          linkColor={() => 'rgba(59, 130, 246, 0.4)'}
          linkWidth={1.5}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          backgroundColor="#161b22"
          cooldownTicks={100}
        />
      </div>
    </div>
  );
}
