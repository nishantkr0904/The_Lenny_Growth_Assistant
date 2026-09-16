import {
  Artifact,
  ArtifactListItem,
  HealthStatus,
  ProviderStatusResponse,
  Session,
  SessionDetail,
} from '../types';

const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchProviders(): Promise<ProviderStatusResponse> {
  const res = await fetch(`${API_BASE}/providers`);
  if (!res.ok) {
    throw new Error(`Failed to load providers: ${res.statusText}`);
  }
  return res.json();
}

export async function selectProvider(provider: 'ollama' | 'anthropic' | 'gemini' | 'openai' | 'groq'): Promise<ProviderStatusResponse> {
  const res = await fetch(`${API_BASE}/providers/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to select provider');
  }
  return res.json();
}

export async function saveAnthropicKey(apiKey: string): Promise<ProviderStatusResponse> {
  const res = await fetch(`${API_BASE}/providers/anthropic/key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to save Anthropic API key');
  }
  return res.json();
}

export async function saveGeminiKey(apiKey: string): Promise<ProviderStatusResponse> {
  const res = await fetch(`${API_BASE}/providers/gemini/key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to save Google Gemini API key');
  }
  return res.json();
}

export async function saveOpenAIKey(apiKey: string): Promise<ProviderStatusResponse> {
  const res = await fetch(`${API_BASE}/providers/openai/key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to save OpenAI API key');
  }
  return res.json();
}

export async function saveGroqKey(apiKey: string): Promise<ProviderStatusResponse> {
  const res = await fetch(`${API_BASE}/providers/groq/key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to save Groq API key');
  }
  return res.json();
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) {
    throw new Error(`Failed to load sessions: ${res.statusText}`);
  }
  return res.json();
}

export async function createSession(title?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title || 'New Research Session' }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create session: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSession(id: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/sessions/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch session: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete session: ${res.statusText}`);
  }
}

export async function createArtifact(params: {
  session_id: string;
  artifact_type: string;
  title?: string;
  message_id?: string;
}): Promise<Artifact> {
  const res = await fetch(`${API_BASE}/artifacts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to create artifact');
  }
  return res.json();
}

export async function fetchArtifact(id: string): Promise<Artifact> {
  const res = await fetch(`${API_BASE}/artifacts/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch artifact: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSessionArtifacts(sessionId: string): Promise<ArtifactListItem[]> {
  const res = await fetch(`${API_BASE}/artifacts/session/${sessionId}`);
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export interface StreamEventHandlers {
  onThinking?: (data: { status: string; query?: string; agent?: string }) => void;
  onEvidence?: (data: { tier: string; score: number; can_synthesize: boolean; chunk_count?: number }) => void;
  onDelta?: (data: { text: string }) => void;
  onCitation?: (data: any) => void;
  onDone?: (data: { message_id: string; tier?: string; sources?: any[]; agent?: string; latency_ms?: number }) => void;
  onError?: (err: Error) => void;
}

export async function streamMessage(
  sessionId: string,
  content: string,
  handlers: StreamEventHandlers,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({
      content,
      stream: true,
    }),
    signal,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail || `Server returned ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = 'message';

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const rawData = line.slice(5).trim();
          try {
            const data = JSON.parse(rawData);
            if (currentEvent === 'thinking') {
              handlers.onThinking?.(data);
            } else if (currentEvent === 'evidence') {
              handlers.onEvidence?.(data);
            } else if (currentEvent === 'delta') {
              handlers.onDelta?.(data);
            } else if (currentEvent === 'citation') {
              handlers.onCitation?.(data);
            } else if (currentEvent === 'done') {
              handlers.onDone?.(data);
            }
          } catch (parseErr) {
            console.warn('Failed to parse SSE data JSON:', rawData);
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      return;
    }
    handlers.onError?.(err);
    throw err;
  }
}
