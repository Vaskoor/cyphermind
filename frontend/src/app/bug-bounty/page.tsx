'use client';

import { useEffect, useRef, useState } from 'react';
import {
  BookOpen,
  Bug,
  FileUp,
  Globe,
  List,
  Loader2,
  Play,
  Search,
  Shield,
  Wrench,
} from 'lucide-react';
import { bugBountyApi, getErrorMessage, toolsApi } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import SeverityBadge from '@/components/ui/SeverityBadge';
import type { Finding, HuntJob, ToolInfo } from '@/lib/types';

interface WordlistStatus {
  dns_wordlist?: string | null;
  dns_lines?: number;
  web_wordlist?: string | null;
  web_lines?: number;
  params_wordlist?: string | null;
  params_lines?: number;
  wordlist_dir?: string;
  seclists_detected?: boolean;
  recommended_seclists?: Record<string, string[]>;
  env_vars?: Record<string, string>;
}

interface MethodologyPhase {
  id: number;
  name: string;
  title: string;
  description: string;
}

export default function BugBountyPage() {
  const { success, error: toastError } = useToast();
  const [targetUrl, setTargetUrl] = useState('https://');
  const [scope, setScope] = useState('');
  const [notes, setNotes] = useState('');
  const [maxIter, setMaxIter] = useState(15);
  const [runMethodology, setRunMethodology] = useState(true);
  const [pipelineMode, setPipelineMode] = useState<'default' | 'full'>('default');
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<HuntJob | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [wordlists, setWordlists] = useState<WordlistStatus | null>(null);
  const [phases, setPhases] = useState<MethodologyPhase[]>([]);
  const [uploading, setUploading] = useState<string | null>(null);
  const dnsRef = useRef<HTMLInputElement>(null);
  const webRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    toolsApi.list().then((d) => setTools(d.tools)).catch(() => {});
    bugBountyApi.getWordlists().then(setWordlists).catch(() => {});
    bugBountyApi.getMethodology().then((d) => setPhases(d.phases || [])).catch(() => {});
  }, []);

  const refreshWordlists = () => {
    bugBountyApi.getWordlists().then(setWordlists).catch(() => {});
  };

  const uploadWordlist = async (kind: 'dns' | 'web', file: File) => {
    setUploading(kind);
    try {
      const result = await bugBountyApi.uploadWordlist(kind, file);
      success('Wordlist uploaded', `${result.lines} lines → ${result.path}`);
      refreshWordlists();
    } catch (err) {
      toastError('Upload failed', getErrorMessage(err));
    } finally {
      setUploading(null);
    }
  };

  const startHunt = async () => {
    if (!targetUrl.trim()) return;
    setLoading(true);
    setJob(null);
    try {
      const scopeDomains = scope.split(',').map((s) => s.trim()).filter(Boolean);
      const { job_id } = await bugBountyApi.startHunt(
        targetUrl,
        scopeDomains,
        maxIter,
        notes,
        runMethodology,
        pipelineMode,
      );
      success('Hunt started', `Job ${job_id} — methodology + autonomous agent running`);
      poll(job_id);
    } catch (err) {
      toastError('Failed to start hunt', getErrorMessage(err));
      setLoading(false);
    }
  };

  const poll = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await bugBountyApi.getHunt(jobId);
        setJob(status as HuntJob);
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
        }
      } catch {
        clearInterval(interval);
        setLoading(false);
      }
    }, 4000);
  };

  const findings = (job?.findings || []) as Finding[];
  const reconSummary = (job as Record<string, unknown>)?.recon_summary as Record<string, number> | undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Bug className="h-7 w-7 text-accent" />
          Autonomous Bug Bounty Copilot
        </h1>
        <p className="mt-1 text-sm text-muted">
          13-phase Cybernote methodology: subdomain enum, URL discovery, JS secrets, nuclei, RAG enrichment
        </p>
      </div>

      {/* Wordlists section */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <List className="h-5 w-5 text-accent" />
          Wordlists & SecLists
        </h2>
        <div className="grid gap-4 md:grid-cols-3 text-sm">
          <div className="rounded-lg bg-background/50 p-4">
            <p className="text-muted mb-1">DNS wordlist</p>
            <p className="font-mono text-xs text-accent truncate">{wordlists?.dns_wordlist || 'builtin default'}</p>
            <p className="text-muted mt-1">{wordlists?.dns_lines ?? 0} lines</p>
            <input
              ref={dnsRef}
              type="file"
              accept=".txt,.lst"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && uploadWordlist('dns', e.target.files[0])}
            />
            <button
              onClick={() => dnsRef.current?.click()}
              disabled={uploading === 'dns'}
              className="mt-2 flex items-center gap-1 text-xs text-accent hover:underline"
            >
              {uploading === 'dns' ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileUp className="h-3 w-3" />}
              Upload DNS wordlist
            </button>
          </div>
          <div className="rounded-lg bg-background/50 p-4">
            <p className="text-muted mb-1">Web wordlist</p>
            <p className="font-mono text-xs text-accent truncate">{wordlists?.web_wordlist || 'builtin default'}</p>
            <p className="text-muted mt-1">{wordlists?.web_lines ?? 0} lines</p>
            <input
              ref={webRef}
              type="file"
              accept=".txt,.lst"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && uploadWordlist('web', e.target.files[0])}
            />
            <button
              onClick={() => webRef.current?.click()}
              disabled={uploading === 'web'}
              className="mt-2 flex items-center gap-1 text-xs text-accent hover:underline"
            >
              {uploading === 'web' ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileUp className="h-3 w-3" />}
              Upload web wordlist
            </button>
          </div>
          <div className="rounded-lg bg-background/50 p-4">
            <p className="text-muted mb-1">SecLists</p>
            <p className={wordlists?.seclists_detected ? 'text-green-400' : 'text-yellow-400'}>
              {wordlists?.seclists_detected ? 'Detected on system' : 'Not installed'}
            </p>
            <p className="text-xs text-muted mt-2">
              Set <code className="text-accent">DNS_WORDLIST</code> and <code className="text-accent">WEB_WORDLIST</code> in .env
            </p>
            <p className="text-xs text-muted mt-1 truncate">{wordlists?.wordlist_dir}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4 rounded-xl border border-border bg-surface p-6">
          <div>
            <label className="text-sm text-muted flex items-center gap-2 mb-1">
              <Globe className="h-4 w-4" /> Target URL
            </label>
            <input
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-white"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://target.example.com"
            />
          </div>
          <div>
            <label className="text-sm text-muted mb-1 block">Scope domains (comma-separated)</label>
            <input
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-white"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              placeholder="example.com, *.example.com"
            />
          </div>
          <div>
            <label className="text-sm text-muted mb-1 block">Program notes / rules</label>
            <textarea
              className="w-full h-20 bg-background border border-border rounded-lg px-3 py-2 text-white text-sm"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Out of scope: social engineering, DoS..."
            />
          </div>
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted">Max iterations</label>
              <input
                type="number"
                min={5}
                max={30}
                value={maxIter}
                onChange={(e) => setMaxIter(parseInt(e.target.value, 10))}
                className="w-20 bg-background border border-border rounded px-2 py-1 text-white"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={runMethodology}
                onChange={(e) => setRunMethodology(e.target.checked)}
                className="rounded"
              />
              Run methodology pipeline first
            </label>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted">Pipeline</label>
              <select
                value={pipelineMode}
                onChange={(e) => setPipelineMode(e.target.value as 'default' | 'full')}
                className="bg-background border border-border rounded px-2 py-1 text-white text-sm"
                disabled={!runMethodology}
              >
                <option value="default">Default (6 phases)</option>
                <option value="full">Full (13 phases)</option>
              </select>
            </div>
          </div>
          <button
            onClick={startHunt}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white py-3 rounded-lg font-semibold"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
            {loading ? 'Methodology + hunt in progress...' : 'Launch Autonomous Hunt'}
          </button>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-white font-semibold flex items-center gap-2 mb-3">
              <BookOpen className="h-4 w-4 text-accent" />
              Methodology ({phases.length} phases)
            </h2>
            <ul className="space-y-1.5 max-h-48 overflow-y-auto text-xs">
              {phases.map((p) => (
                <li key={p.id} className="text-muted">
                  <span className="text-accent font-mono">{p.id}.</span>{' '}
                  <span className="text-white">{p.title}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-white font-semibold flex items-center gap-2 mb-3">
              <Wrench className="h-4 w-4 text-accent" />
              Tools ({tools.length})
            </h2>
            <ul className="space-y-2 max-h-48 overflow-y-auto text-xs">
              {tools.map((t) => (
                <li key={t.name} className="rounded-lg bg-background/50 px-2 py-1.5">
                  <span className="font-mono text-accent">{t.name}</span>
                  <span className="ml-2 text-muted capitalize">[{t.category}]</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {job && (
        <div className="rounded-xl border border-border bg-surface p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Hunt Status: {job.job_id}
            </h2>
            <span className={`text-sm font-medium capitalize ${
              job.status === 'completed' ? 'text-green-400' : job.status === 'failed' ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {job.status}
            </span>
          </div>

          {reconSummary && (
            <div className="grid grid-cols-4 gap-3 text-center text-sm">
              {[
                ['Subdomains', reconSummary.subdomains],
                ['Alive', reconSummary.alive_hosts],
                ['URLs', reconSummary.urls],
                ['JS files', reconSummary.js_urls],
              ].map(([label, val]) => (
                <div key={String(label)} className="rounded-lg bg-background/50 p-3">
                  <p className="text-2xl font-bold text-accent">{val ?? 0}</p>
                  <p className="text-muted text-xs">{label}</p>
                </div>
              ))}
            </div>
          )}

          {job.summary && (
            <div className="rounded-lg bg-background/50 p-4 text-sm text-slate-300 whitespace-pre-wrap">
              {job.summary}
            </div>
          )}

          {job.error && <p className="text-red-400 text-sm">{job.error}</p>}

          {job.reports && job.reports.length > 0 && (
            <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-4">
              <h3 className="text-white font-medium mb-2">Reports generated</h3>
              <ul className="space-y-2 text-sm">
                {job.reports.map((r) => (
                  <li key={r.id} className="flex items-center justify-between gap-2">
                    <span className="text-muted">{r.title}</span>
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/reports/${r.id}/html`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:underline shrink-0"
                    >
                      View report →
                    </a>
                  </li>
                ))}
              </ul>
              <a href="/reports" className="mt-3 inline-block text-xs text-accent hover:underline">
                All reports →
              </a>
            </div>
          )}

          {findings.length > 0 && (
            <div>
              <h3 className="text-white font-medium mb-2">Findings ({findings.length})</h3>
              <div className="space-y-2">
                {findings.map((f, i) => (
                  <div key={i} className="rounded-lg border border-border bg-background/30 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge severity={f.severity as 'high'} />
                      <span className="font-medium text-white">{f.title}</span>
                    </div>
                    <p className="text-sm text-muted">{f.description}</p>
                    {f.payload && <pre className="mt-2 text-xs text-green-400 overflow-x-auto">{f.payload}</pre>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {job.tool_calls && job.tool_calls.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-muted flex items-center gap-1">
                <Search className="h-4 w-4" />
                Tool calls ({job.tool_calls.length})
              </summary>
              <pre className="mt-2 max-h-64 overflow-auto text-xs bg-background p-3 rounded">
                {JSON.stringify(job.tool_calls, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
