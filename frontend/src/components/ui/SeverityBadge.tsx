import type { Severity } from '@/lib/types';

const severityConfig: Record<
  Severity,
  { label: string; className: string; dot: string }
> = {
  critical: {
    label: 'Critical',
    className: 'bg-danger/15 text-danger border-danger/30',
    dot: 'bg-danger',
  },
  high: {
    label: 'High',
    className: 'bg-warning/15 text-warning border-warning/30',
    dot: 'bg-warning',
  },
  medium: {
    label: 'Medium',
    className: 'bg-accent/15 text-accent border-accent/30',
    dot: 'bg-accent',
  },
  low: {
    label: 'Low',
    className: 'bg-info/15 text-info border-info/30',
    dot: 'bg-info',
  },
  info: {
    label: 'Info',
    className: 'bg-muted/15 text-muted border-border',
    dot: 'bg-muted',
  },
};

interface SeverityBadgeProps {
  severity: Severity;
  size?: 'sm' | 'md';
}

export default function SeverityBadge({ severity, size = 'sm' }: SeverityBadgeProps) {
  const config = severityConfig[severity] ?? severityConfig.info;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${config.className} ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}
