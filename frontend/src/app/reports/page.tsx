'use client';

import { useEffect, useState } from 'react';
import {
  Download,
  ExternalLink,
  Eye,
  FileText,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import Link from 'next/link';
import { getErrorMessage, reportsApi } from '@/lib/api';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import type { Report } from '@/lib/types';

const statusStyles: Record<Report['status'], string> = {
  generating: 'bg-warning/15 text-warning',
  ready: 'bg-success/15 text-success',
  failed: 'bg-danger/15 text-danger',
};

const typeStyles: Record<string, string> = {
  recon: 'bg-cyan-500/15 text-cyan-400',
  combined: 'bg-accent/15 text-accent',
  executive: 'bg-purple-500/15 text-purple-400',
  findings: 'bg-orange-500/15 text-orange-400',
};

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState<string | number | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const data = await reportsApi.list();
      setReports(data);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDownload = async (report: Report) => {
    setDownloading(report.id);
    try {
      const blob = await reportsApi.download(report.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.replace(/[^a-z0-9-_]/gi, '_')}.${report.format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" label="Loading reports..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Reports</h1>
          <p className="mt-1 text-sm text-muted">
            Auto-generated recon and assessment reports — one per agent after each run
          </p>
        </div>
        <button
          onClick={fetchReports}
          className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted transition-colors hover:border-accent/30 hover:text-white"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {reports.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-xl border border-border bg-surface">
          <FileText className="mb-3 h-10 w-10 text-muted" />
          <p className="text-sm text-muted">No reports generated yet</p>
          <p className="mt-1 text-xs text-muted">
            Run a bug bounty hunt or engagement — reports appear here automatically
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <div
              key={report.id}
              className="group rounded-xl border border-border bg-surface p-5 transition-all hover:border-accent/30 hover:shadow-glow-sm"
            >
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10">
                  <FileText className="h-5 w-5 text-accent" />
                </div>
                <div className="flex flex-wrap gap-1 justify-end">
                  {report.report_type && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        typeStyles[report.report_type] || 'bg-muted/20 text-muted'
                      }`}
                    >
                      {report.report_type}
                    </span>
                  )}
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusStyles[report.status]}`}
                  >
                    {report.status}
                  </span>
                </div>
              </div>

              <h3 className="mb-1 text-sm font-semibold text-white line-clamp-2">
                {report.title}
              </h3>
              <p className="mb-1 text-xs text-muted">
                {report.agent_name && <span className="text-accent">{report.agent_name}</span>}
                {report.agent_name && ' · '}
                {new Date(report.created_at).toLocaleString()} · {report.format.toUpperCase()}
              </p>
              {report.findings_count !== undefined && report.report_type !== 'recon' && (
                <p className="mb-4 text-xs text-muted">{report.findings_count} finding(s)</p>
              )}
              {report.report_type === 'recon' && (
                <p className="mb-4 text-xs text-cyan-400">Recon intelligence report</p>
              )}

              {report.status === 'ready' && (
                <div className="flex gap-2">
                  <a
                    href={reportsApi.getHtmlUrl(report.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-background py-2 text-xs font-medium text-white transition-colors hover:bg-background/80"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    View
                  </a>
                  <button
                    onClick={() => handleDownload(report)}
                    disabled={downloading === report.id}
                    className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-accent/10 py-2 text-xs font-medium text-accent transition-colors hover:bg-accent/20"
                  >
                    {downloading === report.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5" />
                    )}
                    Save
                  </button>
                </div>
              )}

              {report.engagement_id && (
                <Link
                  href={`/engagements/${report.engagement_id}`}
                  className="mt-2 flex items-center gap-1 text-xs text-muted hover:text-accent"
                >
                  <ExternalLink className="h-3 w-3" />
                  Engagement #{report.engagement_id}
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
