import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: { value: number; label: string };
  accent?: 'blue' | 'green' | 'red' | 'yellow' | 'cyan';
}

const accentStyles = {
  blue: 'bg-accent/10 text-accent border-accent/20',
  green: 'bg-success/10 text-success border-success/20',
  red: 'bg-danger/10 text-danger border-danger/20',
  yellow: 'bg-warning/10 text-warning border-warning/20',
  cyan: 'bg-info/10 text-info border-info/20',
};

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  accent = 'blue',
}: StatCardProps) {
  return (
    <div className="group rounded-xl border border-border bg-surface p-5 transition-all duration-200 hover:border-accent/30 hover:shadow-glow-sm">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted">{title}</p>
          <p className="text-3xl font-bold tracking-tight text-white">{value}</p>
          {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
        </div>
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg border ${accentStyles[accent]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          <span className={trend.value >= 0 ? 'text-success' : 'text-danger'}>
            {trend.value >= 0 ? '+' : ''}
            {trend.value}%
          </span>
          <span className="text-muted">{trend.label}</span>
        </div>
      )}
    </div>
  );
}
