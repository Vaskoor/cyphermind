'use client';

import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Severity } from '@/lib/types';

interface FindingsChartProps {
  data: Record<Severity, number>;
  variant?: 'bar' | 'pie' | 'both';
}

const SEVERITY_COLORS: Record<Severity, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#06b6d4',
  info: '#8b949e',
};

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];

function buildChartData(data: Record<Severity, number>) {
  return SEVERITY_ORDER.map((severity) => ({
    severity: severity.charAt(0).toUpperCase() + severity.slice(1),
    count: data[severity] ?? 0,
    fill: SEVERITY_COLORS[severity],
  })).filter((d) => d.count > 0);
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: { severity: string; count: number } }[];
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-white">{item.severity}</p>
      <p className="text-xs text-muted">{item.count} findings</p>
    </div>
  );
}

export default function FindingsChart({ data, variant = 'both' }: FindingsChartProps) {
  const chartData = buildChartData(data);
  const total = chartData.reduce((sum, d) => sum + d.count, 0);

  if (total === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-border bg-surface">
        <p className="text-sm text-muted">No findings data available</p>
      </div>
    );
  }

  return (
    <div className={`grid gap-4 ${variant === 'both' ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
      {(variant === 'bar' || variant === 'both') && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <h3 className="mb-4 text-sm font-semibold text-white">Findings by Severity</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <XAxis
                dataKey="severity"
                tick={{ fill: '#8b949e', fontSize: 12 }}
                axisLine={{ stroke: '#2d333b' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#8b949e', fontSize: 12 }}
                axisLine={{ stroke: '#2d333b' }}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.severity} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {(variant === 'pie' || variant === 'both') && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <h3 className="mb-4 text-sm font-semibold text-white">Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="count"
                nameKey="severity"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
              >
                {chartData.map((entry) => (
                  <Cell key={entry.severity} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span style={{ color: '#8b949e', fontSize: 12 }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
