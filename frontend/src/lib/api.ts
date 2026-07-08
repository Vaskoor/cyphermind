import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  CreateEngagementPayload,
  DashboardStats,
  Engagement,
  Finding,
  LLMStatus,
  OllamaStatus,
  Report,
  SelfPlayGame,
  SystemSettings,
  User,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function wsUrl(path: string): string {
  const base = API_BASE.replace(/^http/, 'ws');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalized}`;
}

function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    headers: { 'Content-Type': 'application/json' },
  });

  client.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('cyphermind_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  });

  return client;
}

export const api = createClient();

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string | { msg: string }[] }>;
    const detail = axiosError.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ');
    return axiosError.message;
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred';
}

export const authApi = {
  login: async (username: string, password: string) => {
    const { data } = await api.post<{ access_token: string; token_type: string }>('/auth/login', {
      username,
      password,
    });
    return data;
  },

  register: async (email: string, username: string, password: string) => {
    const { data } = await api.post<User>('/auth/register', {
      email,
      username,
      password,
    });
    return data;
  },
};

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const { data } = await api.get<{
      engagements: Record<string, number>;
      findings_by_severity: Record<string, number>;
      recent_activity: Array<{
        id: number;
        engagement_id: number;
        agent_name: string;
        status: string;
        findings_count: number;
        started_at: string | null;
      }>;
    }>('/dashboard/stats');

    const eng = data.engagements || {};
    const total = Object.values(eng).reduce((a, b) => a + b, 0);
    const active = (eng.running || 0) + (eng.pending || 0);
    const sev = data.findings_by_severity || {};

    return {
      total_engagements: total,
      active_engagements: active,
      total_findings: Object.values(sev).reduce((a, b) => a + b, 0),
      findings_by_severity: {
        critical: sev.critical || 0,
        high: sev.high || 0,
        medium: sev.medium || 0,
        low: sev.low || 0,
        info: sev.info || 0,
      },
      recent_agent_runs: (data.recent_activity || []).map((r) => ({
        id: String(r.id),
        agent_name: r.agent_name,
        status: r.status as 'pending' | 'running' | 'completed' | 'failed',
        started_at: r.started_at || new Date().toISOString(),
        findings_count: r.findings_count,
      })),
      recent_findings: [],
    };
  },
};

export const findingsApi = {
  list: async (params?: { engagement_id?: string; severity?: string; page?: number }) => {
    const { data } = await api.get<{ items: Finding[]; total: number }>('/findings', { params });
    return data;
  },
};

export const engagementsApi = {
  list: async () => {
    const { data } = await api.get<Engagement[]>('/engagements');
    return data;
  },

  get: async (id: string) => {
    const { data } = await api.get<Engagement>(`/engagements/${id}`);
    return data;
  },

  create: async (payload: CreateEngagementPayload) => {
    const targets = [];
    if (payload.target_url || payload.repo_path || payload.ip_address) {
      targets.push({
        name: `${payload.name} Target`,
        target_type: payload.target_type || 'web',
        url: payload.target_url || null,
        ip_address: payload.ip_address || null,
        code_path: payload.repo_path || null,
      });
    }
    const { data } = await api.post<Engagement>('/engagements', {
      name: payload.name,
      description: payload.description,
      targets,
      mode: payload.mode || 'standard',
      scope_domains: payload.scope_domains || [],
    });
    return data;
  },

  delete: async (id: string) => {
    await api.delete(`/engagements/${id}`);
  },

  getThreatModel: async (id: string) => {
    const { data } = await api.get(`/engagements/${id}/threat-model`);
    return data;
  },

  runAgents: async (
    id: string,
    opts?: { agentName?: string; mode?: 'standard' | 'bug_bounty' | 'autonomous'; scopeDomains?: string[]; maxIterations?: number }
  ) => {
    const { data } = await api.post('/agents/execute', {
      engagement_id: parseInt(id, 10),
      agent_name: opts?.agentName || null,
      mode: opts?.mode || 'standard',
      scope_domains: opts?.scopeDomains || [],
      max_iterations: opts?.maxIterations || 15,
    });
    const agents = Array.isArray(data.agents) ? data.agents.join(', ') : data.agents;
    return { message: `Started: ${agents}`, ...data };
  },

  generateReport: async (id: string, format: 'html' | 'json' | 'sarif' = 'html') => {
    const { data } = await api.post<Report>('/reports', {
      engagement_id: parseInt(id, 10),
      format,
    });
    return data;
  },
};

export const agentApi = {
  getPolicy: async () => {
    const { data } = await api.get('/agents/q-policy');
    return data;
  },
};

export const chatApi = {
  send: async (message: string, history?: object[], useTools = true) => {
    const { data } = await api.post<{
      answer: string;
      citations: object[];
      tool_calls?: object[];
      findings?: Finding[];
    }>('/chat', { message, history, use_tools: useTools });
    return {
      reply: data.answer,
      citations: data.citations,
      toolCalls: data.tool_calls || [],
      findings: data.findings || [],
    };
  },
};

export const toolsApi = {
  list: async () => {
    const { data } = await api.get<{ tools: ToolInfo[]; count: number }>('/tools');
    return data;
  },
  invoke: async (tool_name: string, arguments_: object, scope_domains: string[] = []) => {
    const { data } = await api.post('/tools/invoke', {
      tool_name,
      arguments: arguments_,
      scope_domains,
    });
    return data;
  },
};

export const bugBountyApi = {
  getMethodology: async () => {
    const { data } = await api.get('/bug-bounty/methodology');
    return data;
  },
  getWordlists: async () => {
    const { data } = await api.get('/wordlists/status');
    return data;
  },
  uploadWordlist: async (kind: 'dns' | 'web' | 'params', file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const { data } = await api.post(`/wordlists/upload/${kind}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  startHunt: async (
    target_url: string,
    scope_domains: string[] = [],
    max_iterations = 15,
    notes = '',
    run_methodology = true,
    pipeline_mode: 'default' | 'full' = 'default',
  ) => {
    const { data } = await api.post<{ job_id: string; status: string }>('/bug-bounty/hunt', {
      target_url,
      scope_domains,
      max_iterations,
      notes,
      run_methodology,
      pipeline_mode,
    });
    return data;
  },
  getHunt: async (jobId: string) => {
    const { data } = await api.get(`/bug-bounty/hunt/${jobId}`);
    return data;
  },
};

export const knowledgeApi = {
  query: async (query: string, top_k = 5) => {
    const { data } = await api.post<{ results: Array<{ content: string; score: number; source: string }> }>(
      '/knowledge/query',
      { query, top_k }
    );
    return data;
  },

  ingestFile: async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const { data } = await api.post('/knowledge/ingest', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  analyzeTaint: async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const { data } = await api.post('/knowledge/analyze-taint', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
};

export const selfPlayApi = {
  start: async (target_code: string, language = 'python', max_rounds = 5) => {
    const { data } = await api.post<SelfPlayGame>('/selfplay/start', {
      target_code,
      language,
      max_rounds,
    });
    return data;
  },

  status: async (gameId: number) => {
    const { data } = await api.get<SelfPlayGame>(`/selfplay/status/${gameId}`);
    return data;
  },
};

export const reportsApi = {
  list: async () => {
    const { data } = await api.get<Report[]>('/reports');
    return data;
  },

  generate: async (engagement_id: number, format = 'html') => {
    const { data } = await api.post('/reports', { engagement_id, format });
    return data;
  },

  download: async (reportId: number | string) => {
    const { data } = await api.get<Blob>(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return data;
  },

  getHtmlUrl: (reportId: number | string) => `${API_BASE}/api/v1/reports/${reportId}/html`,

  downloadUrl: (reportId: number | string) => `${API_BASE}/api/v1/reports/${reportId}/download`,
};

export const learningApi = {
  getQTable: () => api.get('/learning/q-table'),
  submitFeedback: (data: object) => api.post('/learning/feedback', data),
  getBTScores: () => api.get('/learning/bradley-terry'),
};

export const settingsApi = {
  get: async (): Promise<SystemSettings> => {
    const { data } = await api.get<SystemSettings>('/settings');
    return data;
  },

  checkLLM: async (): Promise<LLMStatus> => {
    const { data } = await api.get<LLMStatus>('/settings/llm');
    return data;
  },

  /** @deprecated use checkLLM */
  checkOllama: async (): Promise<LLMStatus> => {
    const { data } = await api.get<LLMStatus>('/settings/llm');
    return data;
  },
};
