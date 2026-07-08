'use client';

import { useState } from 'react';
import { Loader2, Play, Swords } from 'lucide-react';
import { getErrorMessage, selfPlayApi } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import type { SelfPlayGame } from '@/lib/types';

const SAMPLE_CODE = `from flask import request
import os

def process_user_input():
    cmd = request.args.get('cmd', '')
    result = os.system(cmd)  # VULNERABLE: OS injection
    return str(result)
`;

export default function SelfPlayPage() {
  const { success, error: toastError } = useToast();
  const [code, setCode] = useState(SAMPLE_CODE);
  const [gameId, setGameId] = useState<number | null>(null);
  const [status, setStatus] = useState<SelfPlayGame | null>(null);
  const [loading, setLoading] = useState(false);

  const poll = (id: number) => {
    const interval = setInterval(async () => {
      try {
        const data = await selfPlayApi.status(id);
        setStatus(data);
        if (data.status === 'completed') clearInterval(interval);
      } catch {
        clearInterval(interval);
      }
    }, 3000);
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      const data = await selfPlayApi.start(code, 'python', 3);
      const id = data.game_id ?? data.id;
      if (id) {
        setGameId(id);
        poll(id);
      }
      success('Self-play started', 'Red vs Blue battle initiated');
    } catch (err) {
      toastError('Failed to start', getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const winnerColor = status?.winner === 'red' ? 'text-red-400' : 'text-green-400';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Swords className="h-6 w-6 text-accent" />
          Self-Play Arena
        </h1>
        <p className="mt-1 text-sm text-muted">
          Red Team LLM attacks, Blue Team LLM defends. Novel patterns flagged for KB ingestion.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-surface p-5">
          <label className="block text-sm font-medium text-slate-300 mb-2">Target Code (Python)</label>
          <textarea
            className="w-full h-64 bg-background border border-border rounded-lg p-4 text-green-400 font-mono text-sm focus:outline-none focus:border-accent"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button
            onClick={handleStart}
            disabled={loading || status?.status === 'running'}
            className="mt-4 w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white py-3 rounded-lg font-medium transition"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {status?.status === 'running' ? 'Battle in progress...' : 'Start Red vs Blue'}
          </button>
        </div>

        <div className="rounded-xl border border-border bg-surface p-6">
          <h2 className="text-white font-semibold mb-4">Game Status</h2>
          {!status && <p className="text-muted">No game running yet.</p>}
          {status && (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted">Status:</span>
                <span className={status.status === 'completed' ? 'text-green-400' : 'text-yellow-400'}>
                  {status.status}
                </span>
              </div>
              {status.winner && (
                <div className="flex justify-between">
                  <span className="text-muted">Winner:</span>
                  <span className={`font-bold ${winnerColor}`}>{status.winner.toUpperCase()} TEAM</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted">Rounds:</span>
                <span className="text-white">{status.total_rounds ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Novel Patterns:</span>
                <span className="text-yellow-400 font-bold">{status.novel_patterns_found ?? 0}</span>
              </div>
              {gameId && <p className="text-xs text-muted font-mono">Game ID: {gameId}</p>}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-red-800/50 bg-red-900/10 p-4">
          <h3 className="text-red-400 font-semibold mb-2">Red Team (Offensive)</h3>
          <p className="text-muted text-sm">Temperature: 0.9 — find exploitable vulnerabilities</p>
        </div>
        <div className="rounded-xl border border-blue-800/50 bg-blue-900/10 p-4">
          <h3 className="text-blue-400 font-semibold mb-2">Blue Team (Defensive)</h3>
          <p className="text-muted text-sm">Temperature: 0.1 — patch vulnerabilities</p>
        </div>
      </div>
    </div>
  );
}
