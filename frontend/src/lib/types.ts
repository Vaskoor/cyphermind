export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface User {
  id: number;
  email: string;
  username: string;
  is_active?: boolean;
  created_at?: string;
}

export interface Finding {
  id: number | string;
  title: string;
  description?: string;
  severity: Severity | string;
  cve_id?: string;
  cwe_id?: string;
  cvss_score?: number;
  confidence?: number;
  is_verified?: boolean;
  is_novel?: boolean;
  payload?: string;
  file_path?: string;
  line_number?: number;
  created_at?: string;
  status?: 'open' | 'confirmed' | 'false_positive' | 'fixed';
  category?: string;
}

export interface AgentRun {
  id: number | string;
  agent_name: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number;
  findings_count?: number;
  rl_reward?: number;
  message?: string;
}

export interface ThreatModel {
  attack_surface: Array<{ vector: string; detail: string; risk: string }>;
  risk_score: number;
  recommended_agents: string[];
  assets?: string[];
  trust_boundaries?: string[];
  attack_vectors?: string[];
}

export interface TaintGraphNode {
  id: string;
  label?: string;
  type?: string;
}

export interface TaintGraphEdge {
  source: string;
  target: string;
  type?: string;
}

export interface TaintGraph {
  nodes: TaintGraphNode[];
  edges?: TaintGraphEdge[];
  links?: TaintGraphEdge[];
}

export interface Engagement {
  id: number | string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  agent_runs?: AgentRun[];
  findings?: Finding[];
  targets?: Array<{
    id: number;
    name: string;
    target_type: string;
    url?: string;
    code_path?: string;
    ip_address?: string;
  }>;
  threat_model?: ThreatModel;
  taint_graph?: TaintGraph;
  target_url?: string;
  repo_path?: string;
}

export interface DashboardStats {
  total_engagements: number;
  active_engagements: number;
  total_findings: number;
  findings_by_severity: Record<Severity, number>;
  recent_agent_runs: AgentRun[];
  recent_findings: Finding[];
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface Report {
  id: number | string;
  title: string;
  format: string;
  status: 'generating' | 'ready' | 'failed';
  report_type?: 'recon' | 'findings' | 'combined' | 'executive' | string;
  agent_name?: string;
  findings_count?: number;
  engagement_id?: number;
  agent_run_id?: number;
  created_at: string;
}

export interface SelfPlayGame {
  game_id?: number;
  id?: number;
  status: string;
  winner?: string;
  total_rounds?: number;
  novel_patterns_found?: number;
}

export interface SystemSettings {
  rl_alpha: number;
  rl_gamma: number;
  rl_epsilon_start: number;
  rl_epsilon_end: number;
  rl_epsilon_decay: number;
  llm_model: string;
  llm_provider?: string;
  nvidia_api_base?: string;
  embedding_model: string;
  api_key_configured?: boolean;
}

export interface LLMStatus {
  online: boolean;
  models: string[];
  provider?: string;
  version?: string;
  error?: string;
  test_reply?: string;
}

/** @deprecated use LLMStatus */
export type OllamaStatus = LLMStatus;

export interface EngagementEvent {
  type: string;
  engagement_id?: number;
  payload?: Record<string, unknown>;
  timestamp?: string;
  agent?: string;
  status?: string;
  findings_count?: number;
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  toolCalls?: object[];
  citations?: object[];
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
  parameters: object;
}

export interface HuntJob {
  job_id: string;
  status: string;
  target?: string;
  findings?: Finding[];
  summary?: string;
  tool_calls?: object[];
  iterations?: number;
  error?: string;
  recon_summary?: Record<string, number>;
  engagement_id?: number;
  reports?: Array<{ id: number; title: string; report_type: string; findings_count: number }>;
}

export interface CreateEngagementPayload {
  name: string;
  description?: string;
  target_url?: string;
  repo_path?: string;
  ip_address?: string;
  target_type?: string;
  mode?: 'standard' | 'bug_bounty' | 'autonomous';
  scope_domains?: string[];
}
