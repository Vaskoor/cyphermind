'use client';

import { useEffect, useState } from 'react';
import {
  Brain,
  CheckCircle,
  Cpu,
  Database,
  Loader2,
  RefreshCw,
  Server,
  Settings2,
  XCircle,
} from 'lucide-react';
import { getErrorMessage, settingsApi } from '@/lib/api';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import type { LLMStatus, SystemSettings } from '@/lib/types';

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 py-3 last:border-0">
      <span className="text-sm text-muted">{label}</span>
      <span className="font-mono text-sm text-white">{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [llm, setLlm] = useState<LLMStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingLlm, setCheckingLlm] = useState(false);
  const [error, setError] = useState('');

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await settingsApi.get();
      setSettings(data);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const checkLlm = async () => {
    setCheckingLlm(true);
    try {
      const status = await settingsApi.checkLLM();
      setLlm(status);
    } catch (err) {
      setLlm({ online: false, models: [], provider: 'nvidia' });
      setError(getErrorMessage(err));
    } finally {
      setCheckingLlm(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    checkLlm();
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" label="Loading settings..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="mt-1 text-sm text-muted">
          System configuration, RL parameters, and service health
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-white">RL Parameters</h2>
          </div>
          {settings ? (
            <div>
              <InfoRow label="Alpha (learning rate)" value={settings.rl_alpha} />
              <InfoRow label="Gamma (discount factor)" value={settings.rl_gamma} />
              <InfoRow label="Epsilon Start" value={settings.rl_epsilon_start} />
              <InfoRow label="Epsilon End" value={settings.rl_epsilon_end} />
              <InfoRow label="Epsilon Decay Steps" value={settings.rl_epsilon_decay} />
            </div>
          ) : (
            <p className="text-sm text-muted">Unable to load RL parameters</p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-accent" />
              <h2 className="text-lg font-semibold text-white">NVIDIA LLM Status</h2>
            </div>
            <button
              onClick={checkLlm}
              disabled={checkingLlm}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent/30 hover:text-white"
            >
              {checkingLlm ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
              Check
            </button>
          </div>

          {llm ? (
            <div>
              <div className="mb-4 flex items-center gap-3">
                {llm.online ? (
                  <CheckCircle className="h-5 w-5 text-success" />
                ) : (
                  <XCircle className="h-5 w-5 text-danger" />
                )}
                <span
                  className={`text-sm font-medium ${llm.online ? 'text-success' : 'text-danger'}`}
                >
                  {llm.online ? 'Online' : 'Offline'}
                </span>
                {llm.provider && (
                  <span className="text-xs text-muted capitalize">{llm.provider}</span>
                )}
              </div>

              {llm.error && (
                <p className="mb-3 text-xs text-danger">{llm.error}</p>
              )}

              {llm.models.length > 0 ? (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                    Model
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {llm.models.map((model) => (
                      <span
                        key={model}
                        className="rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent"
                      >
                        {model}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted">No models configured</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted">Checking LLM status...</p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center gap-2">
            <Cpu className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-white">AI Models</h2>
          </div>
          {settings ? (
            <div>
              <InfoRow label="LLM Provider" value={settings.llm_provider || 'nvidia'} />
              <InfoRow label="LLM Model" value={settings.llm_model} />
              <InfoRow label="API Key" value={settings.api_key_configured ? 'Configured' : 'Missing'} />
              <InfoRow label="Embedding Model (Local)" value={settings.embedding_model} />
            </div>
          ) : (
            <p className="text-sm text-muted">Unable to load model configuration</p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center gap-2">
            <Server className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-white">System Info</h2>
          </div>
          <div>
            <InfoRow label="API URL" value={process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'} />
            <InfoRow label="Frontend" value="Next.js 14.2.4" />
            <InfoRow label="Environment" value={process.env.NODE_ENV || 'development'} />
            <InfoRow
              label="Database"
              value="SQLite (cyphermind.db)"
            />
            <div className="flex items-center justify-between border-b border-border/50 py-3">
              <span className="flex items-center gap-2 text-sm text-muted">
                <Database className="h-4 w-4" />
                Vector Store
              </span>
              <span className="font-mono text-sm text-white">ChromaDB :8001</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
