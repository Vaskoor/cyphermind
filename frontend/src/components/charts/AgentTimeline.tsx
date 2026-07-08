'use client';

import { CheckCircle, Clock, Loader2, XCircle } from 'lucide-react';
import type { AgentRun } from '@/lib/types';

interface AgentTimelineProps {
  runs: AgentRun[];
}

const statusConfig = {
  pending: {
    icon: Clock,
    color: 'text-muted',
    bg: 'bg-muted/10 border-muted/30',
    line: 'bg-muted/30',
  },
  running: {
    icon: Loader2,
    color: 'text-accent',
    bg: 'bg-accent/10 border-accent/30',
    line: 'bg-accent/30',
  },
  completed: {
    icon: CheckCircle,
    color: 'text-success',
    bg: 'bg-success/10 border-success/30',
    line: 'bg-success/30',
  },
  failed: {
    icon: XCircle,
    color: 'text-danger',
    bg: 'bg-danger/10 border-danger/30',
    line: 'bg-danger/30',
  },
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatDuration(start: string, end?: string) {
  if (!end) return 'In progress';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export default function AgentTimeline({ runs }: AgentTimelineProps) {
  if (!runs.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-xl border border-border bg-surface">
        <p className="text-sm text-muted">No agent runs yet</p>
      </div>
    );
  }

  const sorted = [...runs].sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3 className="mb-4 text-sm font-semibold text-white">Agent Run Timeline</h3>
      <div className="space-y-0">
        {sorted.map((run, index) => {
          const config = statusConfig[run.status];
          const Icon = config.icon;
          const isLast = index === sorted.length - 1;

          return (
            <div key={run.id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border ${config.bg}`}
                >
                  <Icon
                    className={`h-4 w-4 ${config.color} ${
                      run.status === 'running' ? 'animate-spin' : ''
                    }`}
                  />
                </div>
                {!isLast && <div className={`w-0.5 flex-1 min-h-[2rem] ${config.line}`} />}
              </div>

              <div className={`flex-1 ${isLast ? '' : 'pb-6'}`}>
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-white">{run.agent_name}</p>
                  <span className={`text-xs font-medium capitalize ${config.color}`}>
                    {run.status}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted">
                  <span>Started {formatTime(run.started_at)}</span>
                  <span>·</span>
                  <span>{formatDuration(run.started_at, run.completed_at)}</span>
                </div>
                {run.message && (
                  <p className="mt-1.5 text-xs text-muted line-clamp-2">{run.message}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
