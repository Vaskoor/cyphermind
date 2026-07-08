'use client';

import { useState } from 'react';
import { Brain, Search, Upload } from 'lucide-react';
import { getErrorMessage, knowledgeApi } from '@/lib/api';
import TaintGraphView from '@/components/graphs/TaintGraphView';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

export default function KnowledgePage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Array<{ content: string; score: number; source: string }>>([]);
  const [taintResult, setTaintResult] = useState<{
    graph?: { nodes: object[]; edges: object[] };
    vulnerable_paths?: Array<{
      source: string;
      sink: string;
      has_sanitizer: boolean;
      confidence: number;
    }>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await knowledgeApi.query(query);
      setResults(data.results || []);
    } catch (err) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const resp = await knowledgeApi.ingestFile(file);
      setUploadMsg(`Ingested ${resp.chunks_added} chunks from ${file.name}`);
    } catch (err) {
      setUploadMsg(getErrorMessage(err));
    }
  };

  const analyzeTaint = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const resp = await knowledgeApi.analyzeTaint(file);
      setTaintResult(resp);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Brain className="h-6 w-6 text-accent" />
          Knowledge Base
        </h1>
        <p className="mt-1 text-sm text-muted">Hybrid RAG: ChromaDB + BM25 + cross-encoder re-ranking</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-white font-semibold mb-3 flex items-center gap-2">
            <Upload className="h-4 w-4" /> Ingest Code File
          </h2>
          <input
            type="file"
            accept=".py,.js,.ts,.java,.go,.rb,.php"
            onChange={uploadFile}
            className="block w-full text-sm text-muted file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-accent file:text-white file:cursor-pointer"
          />
          {uploadMsg && <p className="mt-2 text-green-400 text-sm">{uploadMsg}</p>}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-white font-semibold mb-3">Taint Analysis</h2>
          <input
            type="file"
            accept=".py"
            onChange={analyzeTaint}
            className="block w-full text-sm text-muted file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-orange-600 file:text-white file:cursor-pointer"
          />
        </div>
      </div>

      {loading && <LoadingSpinner label="Processing..." />}

      {taintResult && (
        <div className="rounded-xl border border-orange-700/50 bg-surface p-5">
          <h2 className="text-orange-400 font-semibold mb-3">Taint Analysis Results</h2>
          <p className="text-sm text-muted mb-4">
            Graph: {taintResult.graph?.nodes?.length ?? 0} nodes, {taintResult.graph?.edges?.length ?? 0} edges
          </p>
          {taintResult.graph && (
            <div className="h-64 mb-4 rounded-lg border border-border overflow-hidden">
              <TaintGraphView graph={taintResult.graph as { nodes: { id: string; type?: string; label?: string }[]; edges: { source: string; target: string }[] }} />
            </div>
          )}
          {taintResult.vulnerable_paths?.map((p, i) => (
            <div
              key={i}
              className={`p-3 rounded mb-2 border text-sm ${
                p.has_sanitizer ? 'border-yellow-700 bg-yellow-900/20' : 'border-red-700 bg-red-900/20'
              }`}
            >
              <span className="font-mono text-xs">{p.source} → {p.sink}</span>
              <span className={`ml-3 text-xs ${p.has_sanitizer ? 'text-yellow-400' : 'text-red-400'}`}>
                {p.has_sanitizer ? 'Sanitized' : 'UNSANITIZED'} ({(p.confidence * 100).toFixed(0)}%)
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="text-white font-semibold mb-3 flex items-center gap-2">
          <Search className="h-4 w-4" /> Hybrid Search
        </h2>
        <div className="flex gap-3 mb-4">
          <input
            className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-white placeholder-muted focus:outline-none focus:border-accent"
            placeholder="e.g. SQL injection in Django ORM"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
          <button
            onClick={search}
            disabled={loading || !query}
            className="bg-accent hover:bg-accent-hover disabled:opacity-50 text-white px-5 py-2 rounded-lg font-medium transition"
          >
            Search
          </button>
        </div>
        {results.map((r, i) => (
          <div key={i} className="p-4 bg-background rounded-lg mb-3 border border-border">
            <div className="flex justify-between mb-1">
              <span className="text-muted text-xs">{r.source}</span>
              <span className="text-accent text-xs font-mono">score: {r.score?.toFixed(4)}</span>
            </div>
            <pre className="text-slate-300 text-xs whitespace-pre-wrap">{r.content}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
