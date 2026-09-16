export type EvidenceTier = 'strong' | 'limited' | 'conflicting' | 'insufficient' | 'conversational' | 'Strong' | 'Limited' | 'Conflicting' | 'Insufficient' | 'Conversational' | null;

export interface SourceReference {
  id?: string;
  chunk_id: string;
  episode_id?: string;
  title: string;
  guest: string;
  similarity_score?: number;
  quoted_excerpt: string;
  source_identifier?: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  evidence_tier?: EvidenceTier;
  latency_ms?: number;
  model_used?: string;
  created_at: string;
  sources?: SourceReference[];
  isStreaming?: boolean;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages: Message[];
}

export interface Artifact {
  id: string;
  session_id: string;
  message_id?: string;
  artifact_type: 'ship30_essay' | 'markdown' | 'html_card';
  title: string;
  content_raw: string;
  content_html?: string;
  created_at: string;
  sources: SourceReference[];
}

export interface ArtifactListItem {
  id: string;
  session_id: string;
  artifact_type: string;
  title: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  database: string;
  ollama: string;
  provider: string;
  version: string;
}

export type RightPanelView = 'sources' | 'artifact' | null;

export interface ProviderInfo {
  id: 'ollama' | 'anthropic' | 'gemini' | 'openai' | 'groq';
  name: string;
  type: 'local' | 'cloud';
  model: string;
  configured: boolean;
}

export interface ProviderStatusResponse {
  active_provider: 'ollama' | 'anthropic' | 'gemini' | 'openai' | 'groq';
  providers: ProviderInfo[];
}
