'use client';

import Link from 'next/link';
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  PlusCircle,
  Shield,
  Target,
} from 'lucide-react';
import { dashboardApi, getErrorMessage } from '@/lib/api';
import { usePolling } from '@/hooks/usePolling';
import StatCard from '@/components/ui/StatCard';
import FindingsChart from '@/components/charts/FindingsChart';
import AgentTimeline from '@/components/charts/AgentTimeline';
import SeverityBadge from '@/components/ui/SeverityBadge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import type { DashboardStats, Severity } from '@/lib/types';

const emptySeverity: Record<Severity, number> = {
  critical: 0,
  high: 0,
  medium: 0,
  low: 0,
  info: 0,
};

export default function DashboardPage() {
  const { data, error, isLoading } = usePolling<DashboardStats>({
    fetcher: dashboardApi.getStats,
    interval: 10000,
  });

  if (isLoading && !data) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" label="Loading dashboard..." />
      </div>
    );
  }

  const stats = data ?? {
    total_engagements: 0,
    active_engagements: 0,
    total_findings: 0,
    findings_by_severity: emptySeverity,
    recent_agent_runs: [],
    recent_findings: [],
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-muted">
            Security operations overview and live metrics
          </p>
        </div>
        <Link
          href="/engagements/new"
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          <PlusCircle className="h-4 w-4" />
          New Engagement
        </Link>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Backend unavailable: {getErrorMessage(error)}. Showing cached or empty data.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Engagements"
          value={stats.total_engagements}
          icon={Target}
          accent="blue"
        />
        <StatCard
          title="Active Engagements"
          value={stats.active_engagements}
          subtitle="Currently running"
          icon={Bot}
          accent="cyan"
        />
        <StatCard
          title="Total Findings"
          value={stats.total_findings}
          icon={AlertTriangle}
          accent="red"
        />
        <StatCard
          title="Critical Findings"
          value={stats.findings_by_severity.critical ?? 0}
          icon={Shield}
          accent="yellow"
        />
      </div>

      <FindingsChart data={stats.findings_by_severity} variant="both" />

      <div className="grid gap-6 lg:grid-cols-2">
        <AgentTimeline runs={stats.recent_agent_runs} />

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Recent Findings</h3>
            <Link href="/reports" className="text-xs text-accent hover:underline">
              View all
            </Link>
          </div>
          {stats.recent_findings.length === 0 ? (
            <p className="text-sm text-muted">No recent findings</p>
          ) : (
            <div className="space-y-3">
              {stats.recent_findings.slice(0, 5).map((finding) => (
                <Link
                  key={finding.id}
                  href={`/engagements/${finding.engagement_id}`}
                  className="flex items-center justify-between rounded-lg border border-border/50 bg-background/50 px-3 py-2.5 transition-colors hover:border-accent/30"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white">{finding.title}</p>
                    <p className="text-xs text-muted">{finding.category}</p>
                  </div>
                  <SeverityBadge severity={finding.severity} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-5">
        <h3 className="mb-4 text-sm font-semibold text-white">Quick Actions</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { href: '/engagements/new', label: 'Start Engagement', icon: PlusCircle },
            { href: '/chat', label: 'Ask AI Assistant', icon: Bot },
            { href: '/knowledge', label: 'Explore Knowledge', icon: Shield },
            { href: '/selfplay', label: 'Run Self-Play', icon: Target },
          ].map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="group flex items-center justify-between rounded-lg border border-border bg-background/50 px-4 py-3 transition-all hover:border-accent/30 hover:shadow-glow-sm"
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4 text-accent" />
                <span className="text-sm font-medium text-white">{label}</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
