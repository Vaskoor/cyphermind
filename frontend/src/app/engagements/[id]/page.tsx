'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  Download,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  Shield,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { engagementsApi, getErrorMessage } from '@/lib/api';
import { useEngagementEvents } from '@/hooks/useEngagementEvents';
import { useStore } from '@/store/useStore';
import { useToast } from '@/components/ui/Toast';
import AgentTimeline from '@/components/charts/AgentTimeline';
import TaintGraphView from '@/components/graphs/TaintGraphView';
import SeverityBadge from '@/components/ui/SeverityBadge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import type { AgentRun, Engagement, Finding } from '@/lib/types';

export default function EngagementDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { addFinding, addNotification } = useStore();
  const { success, error: toastError } = useToast();

  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runningAgents, setRunningAgents] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);

  const [threatModel, setThreatModel] = useState<Engagement['threat_model'] | null>(null);

  const fetchEngagement = useCallback(async () => {
    try {
      const data = await engagementsApi.get(id);
      setEngagement(data);
      setAgentRuns(data.agent_runs ?? []);
      setFindings(data.findings ?? []);
      try {
        const tm = await engagementsApi.getThreatModel(id);
        setThreatModel(tm as Engagement['threat_model']);
      } catch {
        setThreatModel(null);
      }
      setError('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchEngagement();
  }, [fetchEngagement]);

  const { connected, events, reconnect } = useEngagementEvents({
    engagementId: id,
    enabled: !!engagement,
    onEvent: (event) => {
      if (event.type === 'agent_started' || event.type === 'agent_completed' || event.type === 'agent_failed') {
        const run = (event.payload || event) as unknown as AgentRun;
        setAgentRuns((prev) => {
          const existing = prev.findIndex((r) => String(r.id) === String(run.id));
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = { ...updated[existing], ...run };
            return updated;
          }
          return [{ ...run, agent_name: run.agent_name || String(event.agent || '') }, ...prev];
        });
      }
      if (event.type === 'finding_discovered') {
        const finding = (event.payload || event) as unknown as Finding;
        setFindings((prev) => [finding, ...prev]);
        addFinding(finding);
        addNotification({
          id: String(Date.now()),
          type: 'warning',
          title: 'New Finding',
          message: finding.title,
          timestamp: new Date().toISOString(),
          read: false,
        });
      }
      if (event.type === 'status_update') {
        fetchEngagement();
      }
    },
  });

  const handleRunAgents = async () => {
    setRunningAgents(true);
    try {
      const result = await engagementsApi.runAgents(id);
      success('Agents started', result.message);
    } catch (err) {
      toastError('Failed to start agents', getErrorMessage(err));
    } finally {
      setRunningAgents(false);
    }
  };

  const handleAutonomousHunt = async () => {
    setRunningAgents(true);
    const scopeDomains = target?.url
      ? [new URL(target.url.startsWith('http') ? target.url : `https://${target.url}`).hostname]
      : [];
    try {
      const result = await engagementsApi.runAgents(id, {
        mode: 'bug_bounty',
        scopeDomains,
        maxIterations: 15,
      });
      success('Autonomous hunt started', result.message);
    } catch (err) {
      toastError('Failed to start hunt', getErrorMessage(err));
    } finally {
      setRunningAgents(false);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const report = await engagementsApi.generateReport(id, 'html');
      success('Report generated', `Report #${report.id} is ready`);
    } catch (err) {
      toastError('Report generation failed', getErrorMessage(err));
    } finally {
      setGeneratingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" label="Loading engagement..." />
      </div>
    );
  }

  if (error && !engagement) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-4">
        <p className="text-danger">{error}</p>
        <button
          onClick={fetchEngagement}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm text-white"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    );
  }

  if (!engagement) return null;

  const target = engagement.targets?.[0];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/dashboard"
            className="mb-3 inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-white">{engagement.name}</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">{engagement.description}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted">
            <span
              className={`rounded-full px-2.5 py-0.5 font-medium capitalize ${
                engagement.status === 'active'
                  ? 'bg-success/15 text-success'
                  : engagement.status === 'completed'
                    ? 'bg-accent/15 text-accent'
                    : 'bg-muted/15 text-muted'
              }`}
            >
              {engagement.status}
            </span>
            {target?.url && <span>Target: {target.url}</span>}
            {target?.code_path && <span>Repo: {target.code_path}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={reconnect}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs ${
              connected
                ? 'border-success/30 text-success'
                : 'border-danger/30 text-danger'
            }`}
            title={connected ? 'WebSocket connected' : 'WebSocket disconnected'}
          >
            {connected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            {connected ? 'Live' : 'Offline'}
          </button>
          <button
            onClick={handleAutonomousHunt}
            disabled={runningAgents}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700"
          >
            {runningAgents ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Autonomous Hunt
          </button>
          <button
            onClick={handleRunAgents}
            disabled={runningAgents}
            className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            {runningAgents ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Run Agents
          </button>
          <button
            onClick={handleGenerateReport}
            disabled={generatingReport}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm text-white transition-colors hover:border-accent/30"
          >
            {generatingReport ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Generate Report
          </button>
        </div>
      </div>

      {threatModel && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-accent" />
              <h2 className="text-lg font-semibold text-white">Threat Model</h2>
            </div>
            <span className="rounded-full bg-accent/15 px-3 py-1 text-sm font-mono text-accent">
              Risk: {((threatModel.risk_score ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                Attack Surface
              </h3>
              <ul className="space-y-2">
                {(threatModel.attack_surface || []).map((item, i) => (
                  <li key={i} className="flex items-center justify-between text-sm text-white rounded-lg bg-background/50 px-3 py-2">
                    <span>{item.vector}: {item.detail}</span>
                    <span className={`text-xs capitalize ${
                      item.risk === 'high' ? 'text-danger' : item.risk === 'medium' ? 'text-warning' : 'text-muted'
                    }`}>{item.risk}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                Recommended Agents
              </h3>
              <div className="flex flex-wrap gap-2">
                {(threatModel.recommended_agents || []).map((agent) => (
                  <span key={agent} className="rounded-full bg-accent/15 px-3 py-1 text-xs font-medium text-accent">
                    {agent}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <AgentTimeline runs={agentRuns} />

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center gap-2">
            <Bot className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-white">Live Events</h2>
            <span className="text-xs text-muted">({events.length})</span>
          </div>
          {events.length === 0 ? (
            <p className="text-sm text-muted">Waiting for agent events...</p>
          ) : (
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {events.slice(0, 20).map((event, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-accent">{event.type}</span>
                  <span className="ml-2 text-muted">
                    {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-white">Findings</h2>
            <span className="rounded-full bg-accent/15 px-2 py-0.5 text-xs font-medium text-accent">
              {findings.length}
            </span>
          </div>
        </div>
        {findings.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-muted">No findings yet. Run agents to start analysis.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Location</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((finding) => (
                  <tr key={finding.id}>
                    <td>
                      <SeverityBadge severity={finding.severity} />
                    </td>
                    <td>
                      <p className="font-medium">{finding.title}</p>
                      <p className="mt-0.5 line-clamp-1 text-xs text-muted">
                        {finding.description}
                      </p>
                    </td>
                    <td className="text-muted">{finding.category}</td>
                    <td className="font-mono text-xs text-muted">
                      {finding.file_path
                        ? `${finding.file_path}${finding.line_number ? `:${finding.line_number}` : ''}`
                        : '—'}
                    </td>
                    <td>
                      <span className="capitalize text-muted">{finding.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {engagement.taint_graph && engagement.taint_graph.nodes.length > 0 && (
        <TaintGraphView graph={engagement.taint_graph} />
      )}
    </div>
  );
}
