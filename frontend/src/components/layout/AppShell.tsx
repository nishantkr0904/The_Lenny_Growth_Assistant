import React, { useState, useEffect } from 'react';
import {
  Artifact,
  HealthStatus,
  Message,
  RightPanelView,
  Session,
  SessionDetail,
  SourceReference,
} from '../../types';
import {
  createArtifact,
  createSession,
  deleteSession,
  fetchHealth,
  fetchSession,
  fetchSessions,
  streamMessage,
} from '../../services/api';
import { Header } from './Header';
import { SessionSidebar } from '../sessions/SessionSidebar';
import { ConversationView } from '../chat/ConversationView';
import { Composer } from '../chat/Composer';
import { SourceDrawer } from '../chat/SourceDrawer';
import { ArtifactViewer } from '../artifacts/ArtifactViewer';
import { ArtifactTypeSelector } from '../artifacts/ArtifactTypeSelector';

export const AppShell: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<SessionDetail | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState<string>('');

  const [rightPanel, setRightPanel] = useState<RightPanelView>(null);
  const [selectedSources, setSelectedSources] = useState<SourceReference[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  const [isArtifactModalOpen, setIsArtifactModalOpen] = useState(false);
  const [targetMessageForArtifact, setTargetMessageForArtifact] = useState<Message | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Load health & initial session list on mount
  useEffect(() => {
    fetchHealth().then(setHealth).catch((err) => console.error('Health check failed:', err));
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const list = await fetchSessions();
      setSessions(list);
      if (list.length > 0 && !activeSessionId) {
        selectSession(list[0].id);
      } else if (list.length === 0) {
        handleNewSession();
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  };

  const selectSession = async (id: string) => {
    setActiveSessionId(id);
    setRightPanel(null);
    try {
      const detail = await fetchSession(id);
      setActiveSession(detail);
    } catch (err) {
      console.error('Failed to load session details:', err);
    }
  };

  const handleNewSession = async () => {
    try {
      const newSess = await createSession('New Research Session');
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setActiveSession({
        ...newSess,
        messages: [],
      });
      setRightPanel(null);
    } catch (err) {
      console.error('Failed to create new session:', err);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id) {
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          handleNewSession();
        }
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!activeSessionId || isLoading) return;

    setIsLoading(true);
    setStatusText('Thinking...');

    const userMessageId = `user-${Date.now()}`;
    const assistantMessageId = `asst-${Date.now()}`;

    const userMsg: Message = {
      id: userMessageId,
      session_id: activeSessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    const initialAsstMsg: Message = {
      id: assistantMessageId,
      session_id: activeSessionId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
      sources: [],
    };

    setActiveSession((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        messages: [...prev.messages, userMsg, initialAsstMsg],
      };
    });

    try {
      await streamMessage(activeSessionId, content, {
        onThinking: (data) => {
          if (data.status === 'retrieving') {
            setStatusText('Retrieving transcript evidence from pgvector...');
          } else {
            setStatusText('Analyzing question context...');
          }
        },
        onEvidence: (data) => {
          setStatusText(`Evidence evaluation: Tier ${data.tier.toUpperCase()} (${Math.round(data.score * 100)}% match)`);
          const normalizedTier = (data.tier ? data.tier.toLowerCase() : undefined) as any;
          setActiveSession((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              messages: prev.messages.map((m) =>
                m.id === assistantMessageId ? { ...m, evidence_tier: normalizedTier } : m
              ),
            };
          });
        },
        onDelta: (data) => {
          setStatusText('Streaming verified answer from Pi Agent...');
          setActiveSession((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              messages: prev.messages.map((m) =>
                m.id === assistantMessageId ? { ...m, content: m.content + data.text } : m
              ),
            };
          });
        },
        onDone: (data) => {
          setIsLoading(false);
          setStatusText('');
          const normalizedTier = (data.tier ? data.tier.toLowerCase() : undefined) as any;
          setActiveSession((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              messages: prev.messages.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      id: data.message_id || m.id,
                      isStreaming: false,
                      sources: data.sources || [],
                      evidence_tier: normalizedTier || m.evidence_tier,
                      latency_ms: data.latency_ms,
                    }
                  : m
              ),
            };
          });
          // Refresh sessions list to update message counts & titles
          fetchSessions().then(setSessions);
        },
        onError: (err) => {
          console.error('Streaming error:', err);
          setIsLoading(false);
          setStatusText('');
          setActiveSession((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              messages: prev.messages.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      isStreaming: false,
                      content:
                        m.content ||
                        `An error occurred communicating with the server: ${err.message}. Please check connection or retry.`,
                    }
                  : m
              ),
            };
          });
        },
      });
    } catch (err: any) {
      setIsLoading(false);
      setStatusText('');
    }
  };

  const handleOpenSources = (sources: SourceReference[]) => {
    setSelectedSources(sources);
    setRightPanel('sources');
  };

  const handleOpenArtifactModal = (message: Message) => {
    setTargetMessageForArtifact(message);
    setIsArtifactModalOpen(true);
  };

  const handleGenerateArtifact = async (
    type: 'ship30_essay' | 'markdown' | 'html_card',
    title: string
  ) => {
    if (!activeSessionId) return;

    setIsLoading(true);
    try {
      const artifact = await createArtifact({
        session_id: activeSessionId,
        artifact_type: type,
        title,
        message_id: targetMessageForArtifact?.id,
      });
      setActiveArtifact(artifact);
      setRightPanel('artifact');
      setIsArtifactModalOpen(false);
    } catch (err: any) {
      alert(`Artifact generation failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-100 dark:bg-slate-950 overflow-hidden font-sans transition-colors">
      <Header health={health} onNewSession={handleNewSession} />

      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Sidebar */}
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={selectSession}
          onDeleteSession={handleDeleteSession}
          onNewSession={handleNewSession}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        />

        {/* Center Conversation Workspace */}
        <main className="flex-1 flex flex-col h-full bg-slate-50 dark:bg-slate-900 min-w-0 overflow-hidden relative transition-colors">
          <ConversationView
            messages={activeSession?.messages || []}
            isLoading={isLoading}
            statusText={statusText}
            onOpenSources={handleOpenSources}
            onCreateArtifact={handleOpenArtifactModal}
            onSelectPrompt={handleSendMessage}
          />

          <Composer
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            disabled={!activeSessionId}
          />
        </main>

        {/* Right Contextual Drawer / Viewer */}
        {rightPanel === 'sources' && (
          <SourceDrawer
            sources={selectedSources}
            onClose={() => setRightPanel(null)}
            isOpen={true}
          />
        )}

        {rightPanel === 'artifact' && activeArtifact && (
          <ArtifactViewer
            artifact={activeArtifact}
            onClose={() => setRightPanel(null)}
            isOpen={true}
          />
        )}
      </div>

      {/* Artifact Type Selector Modal */}
      <ArtifactTypeSelector
        isOpen={isArtifactModalOpen}
        onClose={() => setIsArtifactModalOpen(false)}
        onGenerate={handleGenerateArtifact}
        isLoading={isLoading}
        defaultTitle={activeSession?.title ? `${activeSession.title} — Playbook` : undefined}
      />
    </div>
  );
};
