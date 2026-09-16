import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../components/layout/Header';
import { SessionSidebar } from '../components/sessions/SessionSidebar';
import { EvidenceIndicator } from '../components/chat/EvidenceIndicator';
import { RefusalCard } from '../components/chat/RefusalCard';
import { CitationBadge } from '../components/chat/CitationBadge';
import { SourceDrawer } from '../components/chat/SourceDrawer';
import { AnswerBlock } from '../components/chat/AnswerBlock';
import { SafeHtmlPreview } from '../components/artifacts/SafeHtmlPreview';
import { ArtifactViewer } from '../components/artifacts/ArtifactViewer';
import { Artifact, HealthStatus, Message, Session, SourceReference } from '../types';

describe('Header Component', () => {
  it('renders application title and provider badge for Ollama', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'connected',
      ollama: 'reachable',
      provider: 'ollama',
      version: '0.1.0',
    };
    render(<Header health={health} onNewSession={() => {}} />);
    expect(screen.getByText('The Lenny Growth Assistant')).toBeInTheDocument();
    expect(screen.getByText('Ollama (llama3.1:8b)')).toBeInTheDocument();
  });

  it('renders provider badge for Anthropic when configured', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'connected',
      ollama: 'reachable',
      provider: 'anthropic',
      version: '0.1.0',
    };
    render(<Header health={health} onNewSession={() => {}} />);
    expect(screen.getByText('Anthropic (Claude 3.5 Sonnet)')).toBeInTheDocument();
  });

  it('renders provider badge for Gemini when configured', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'connected',
      ollama: 'reachable',
      provider: 'gemini' as any,
      version: '0.1.0',
    };
    render(<Header health={health} onNewSession={() => {}} />);
    expect(screen.getByText('Gemini (gemini-2.5-flash)')).toBeInTheDocument();
  });

  it('toggles provider menu and shows options including Gemini when badge is clicked', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'connected',
      ollama: 'reachable',
      provider: 'ollama',
      version: '0.1.0',
    };
    render(<Header health={health} onNewSession={() => {}} />);
    const badgeButton = screen.getByRole('button', { name: /Select LLM generation provider/i });
    fireEvent.click(badgeButton);

    expect(screen.getByText('Generation Provider')).toBeInTheDocument();
    expect(screen.getByText(/Ollama · Local/i)).toBeInTheDocument();
    expect(screen.getByText(/Google Gemini · Cloud/i)).toBeInTheDocument();
    expect(screen.getByText(/Anthropic · Cloud/i)).toBeInTheDocument();
  });

  it('clicking unconfigured Gemini opens API key form while Ollama remains active', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'connected',
      ollama: 'reachable',
      provider: 'ollama',
      version: '0.1.0',
    };
    render(<Header health={health} onNewSession={() => {}} />);
    const badgeButton = screen.getByRole('button', { name: /Select LLM generation provider/i });
    fireEvent.click(badgeButton);

    // Click Google Gemini card
    const geminiCard = screen.getByText(/Google Gemini · Cloud/i);
    fireEvent.click(geminiCard);

    // Form appears asking for Gemini key
    expect(screen.getByText(/Enter Google Gemini API Key:/i)).toBeInTheDocument();
    // Ollama remains active in header badge
    expect(screen.getByText('Ollama (llama3.1:8b)')).toBeInTheDocument();

    // Cancel button resets form
    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);
    expect(screen.queryByText(/Enter Google Gemini API Key:/i)).toBeNull();
  });

  it('toggles dark mode theme and adds dark class to documentElement', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'connected',
      ollama: 'reachable',
      provider: 'ollama',
      version: '0.1.0',
    };
    render(<Header health={health} onNewSession={() => {}} />);
    const themeBtn = screen.getByRole('button', { name: /Switch to dark mode|Switch to light mode/i });
    expect(themeBtn).toBeInTheDocument();

    // Toggle theme
    fireEvent.click(themeBtn);
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    // Toggle back
    fireEvent.click(themeBtn);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});

describe('Grounding Trust UX Components', () => {
  it('renders EvidenceIndicator correctly for Strong, Limited, and Conflicting tiers (case-insensitive)', () => {
    const { rerender } = render(<EvidenceIndicator tier="strong" sourcesCount={2} />);
    expect(screen.getByText(/Strong Evidence · 2 sources/i)).toBeInTheDocument();

    rerender(<EvidenceIndicator tier="limited" sourcesCount={1} />);
    expect(screen.getByText(/Limited Evidence · 1 source/i)).toBeInTheDocument();

    rerender(<EvidenceIndicator tier="conflicting" sourcesCount={3} />);
    expect(screen.getByText(/Contrasting Perspectives · 3 sources/i)).toBeInTheDocument();

    // Verify capitalized values from backend
    rerender(<EvidenceIndicator tier={'Strong' as any} sourcesCount={2} />);
    expect(screen.getByText(/Strong Evidence · 2 sources/i)).toBeInTheDocument();

    rerender(<EvidenceIndicator tier={'Limited' as any} sourcesCount={1} />);
    expect(screen.getByText(/Limited Evidence · 1 source/i)).toBeInTheDocument();

    rerender(<EvidenceIndicator tier={'Insufficient' as any} sourcesCount={0} />);
    expect(screen.queryByText(/Evidence/i)).toBeNull();
  });

  it('renders RefusalCard for Insufficient evidence with zero hallucinations', () => {
    const refusalText = 'I could not find guidance on this topic in Lenny\'s Podcast transcripts.';
    render(<RefusalCard content={refusalText} />);
    expect(screen.getByText(/Insufficient Corpus Evidence/i)).toBeInTheDocument();
    expect(screen.getByText(refusalText)).toBeInTheDocument();
    expect(screen.getByText(/Zero ungrounded speculation is permitted/i)).toBeInTheDocument();
  });

  it('AnswerBlock renders RefusalCard and omits Create Artifact button on Insufficient tier', () => {
    const refusalMessage: Message = {
      id: 'msg-refusal',
      session_id: 'sess-1',
      role: 'assistant',
      content: 'There is no information about quantum chromodynamics in Lenny\'s Podcast.',
      evidence_tier: 'Insufficient' as any,
      sources: [],
      created_at: new Date().toISOString(),
    };

    const onCreateArtifact = vi.fn();
    const onOpenSources = vi.fn();

    const { rerender } = render(
      <AnswerBlock
        message={refusalMessage}
        onCreateArtifact={onCreateArtifact}
        onOpenSources={onOpenSources}
      />
    );

    // Must render RefusalCard
    expect(screen.getByText(/Insufficient Corpus Evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/There is no information about quantum chromodynamics/i)).toBeInTheDocument();

    // Must NOT render Create Artifact button
    expect(screen.queryByRole('button', { name: /Create Artifact/i })).toBeNull();
    expect(screen.queryByText(/Create Artifact/i)).toBeNull();

    // Also test lowercase 'insufficient'
    rerender(
      <AnswerBlock
        message={{ ...refusalMessage, evidence_tier: 'insufficient' }}
        onCreateArtifact={onCreateArtifact}
        onOpenSources={onOpenSources}
      />
    );
    expect(screen.getByText(/Insufficient Corpus Evidence/i)).toBeInTheDocument();
    expect(screen.queryByText(/Create Artifact/i)).toBeNull();
  });

  it('AnswerBlock renders Create Artifact button only when valid evidence and sources exist', () => {
    const validMessage: Message = {
      id: 'msg-valid',
      session_id: 'sess-1',
      role: 'assistant',
      content: 'Shreyas Doshi describes the LNO framework as Leverage, Neutral, and Overhead tasks.',
      evidence_tier: 'Limited' as any,
      sources: [
        {
          chunk_id: 'c-1',
          title: 'The art of product management',
          guest: 'Shreyas Doshi',
          similarity_score: 0.737,
          quoted_excerpt: 'L tasks are leverage tasks...',
        },
      ],
      created_at: new Date().toISOString(),
    };

    const onCreateArtifact = vi.fn();
    const onOpenSources = vi.fn();

    render(
      <AnswerBlock
        message={validMessage}
        onCreateArtifact={onCreateArtifact}
        onOpenSources={onOpenSources}
      />
    );

    // Must render valid content and Create Artifact button
    expect(screen.getByText(/Shreyas Doshi describes the LNO framework/i)).toBeInTheDocument();
    const ctaButton = screen.getByRole('button', { name: /Create Artifact/i });
    expect(ctaButton).toBeInTheDocument();

    fireEvent.click(ctaButton);
    expect(onCreateArtifact).toHaveBeenCalledWith(validMessage);
  });

  it('AnswerBlock renders Conversational turn without RefusalCard, EvidenceIndicator, or Create Artifact', () => {
    const convMessage: Message = {
      id: 'msg-conv',
      session_id: 'sess-1',
      role: 'assistant',
      content: 'Hello! How can I help you explore product and growth insights today?',
      evidence_tier: 'Conversational' as any,
      sources: [],
      created_at: new Date().toISOString(),
    };

    const onCreateArtifact = vi.fn();
    const onOpenSources = vi.fn();

    render(
      <AnswerBlock
        message={convMessage}
        onCreateArtifact={onCreateArtifact}
        onOpenSources={onOpenSources}
      />
    );

    // Displays natural prose content
    expect(screen.getByText(/Hello! How can I help you explore product and growth insights today\?/i)).toBeInTheDocument();

    // Must NOT render RefusalCard
    expect(screen.queryByText(/Insufficient Corpus Evidence/i)).toBeNull();

    // Must NOT render Evidence badges or Create Artifact CTA
    expect(screen.queryByText(/Evidence/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /Create Artifact/i })).toBeNull();
    expect(screen.queryByText(/Sources:/i)).toBeNull();
  });

  it('renders CitationBadge and triggers click handler to open drawer', () => {
    const source: SourceReference = {
      chunk_id: 'c-1',
      title: 'Ada Chen Rekhi on Career Growth',
      guest: 'Ada Chen Rekhi',
      quoted_excerpt: 'You must know what mode you are in.',
    };
    const onClick = vi.fn();
    render(<CitationBadge index={1} source={source} onClick={onClick} />);

    const badge = screen.getByRole('button', { name: /Citation 1: Ada Chen Rekhi/i });
    expect(badge).toBeInTheDocument();
    fireEvent.click(badge);
    expect(onClick).toHaveBeenCalledWith(source);
  });

  it('renders SourceDrawer with verified quotes and episode provenance', () => {
    const sources: SourceReference[] = [
      {
        chunk_id: 'c-1',
        title: 'Ada Chen Rekhi on Career Growth',
        guest: 'Ada Chen Rekhi',
        similarity_score: 0.82,
        quoted_excerpt: 'You must know what mode you are in.',
      },
    ];
    render(<SourceDrawer sources={sources} isOpen={true} onClose={() => {}} />);
    expect(screen.getByText(/Verified Transcript Evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/\[1\] Ada Chen Rekhi/i)).toBeInTheDocument();
    expect(screen.getByText(/"You must know what mode you are in."/i)).toBeInTheDocument();
    expect(screen.getByText('82% match')).toBeInTheDocument();
  });
});

describe('Security & Sandboxed Artifact Viewer', () => {
  it('enforces bare iframe sandbox attribute with NO allow-scripts and NO allow-same-origin', () => {
    const htmlContent = '<h1>Sandboxed Card</h1>';
    const { container } = render(<SafeHtmlPreview htmlContent={htmlContent} />);
    const iframe = container.querySelector('iframe');
    expect(iframe).toBeInTheDocument();

    // Security assertions (PRD FR-36, Architecture §12)
    // sandbox attribute must be present and empty string (bare sandbox)
    expect(iframe).toHaveAttribute('sandbox', '');
    const sandboxValue = iframe?.getAttribute('sandbox') || '';
    expect(sandboxValue).not.toContain('allow-scripts');
    expect(sandboxValue).not.toContain('allow-same-origin');
    expect(iframe?.getAttribute('srcdoc')).toBe(htmlContent);
  });

  it('renders ArtifactViewer and toggles between Preview and Source mode', () => {
    const artifact: Artifact = {
      id: 'art-1',
      session_id: 'sess-1',
      artifact_type: 'ship30_essay',
      title: 'Navigating Career Stagnation',
      content_raw: '# Navigating Career Stagnation\n\nShip 30 Essay content.',
      content_html: '<!DOCTYPE html><html><body><h1>Navigating Career Stagnation</h1></body></html>',
      created_at: new Date().toISOString(),
      sources: [],
    };

    render(<ArtifactViewer artifact={artifact} isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Navigating Career Stagnation')).toBeInTheDocument();
    expect(screen.getByText(/Sandboxed Execution/i)).toBeInTheDocument();

    // Switch to Source mode
    const sourceTab = screen.getByRole('button', { name: /Source/i });
    fireEvent.click(sourceTab);
    expect(screen.getByText(/Ship 30 Essay content/i)).toBeInTheDocument();

    // Switch back to Preview mode
    const previewTab = screen.getByRole('button', { name: /Preview/i });
    fireEvent.click(previewTab);
    expect(previewTab).toBeInTheDocument();
  });
});

describe('SessionSidebar Component', () => {
  const sampleSessions: Session[] = [
    {
      id: 'sess-1',
      title: 'Growth Loops Research',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 4,
    },
    {
      id: 'sess-2',
      title: 'PLG Metrics Exploration',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 2,
    },
  ];

  it('renders research sessions list and highlights active session', () => {
    render(
      <SessionSidebar
        sessions={sampleSessions}
        activeSessionId="sess-1"
        onSelectSession={() => {}}
        onDeleteSession={() => {}}
        onNewSession={() => {}}
        isOpen={true}
        onToggle={() => {}}
      />
    );
    expect(screen.getByText('Growth Loops Research')).toBeInTheDocument();
    expect(screen.getByText('PLG Metrics Exploration')).toBeInTheDocument();
  });

  it('calls onDeleteSession with stopPropagation when delete button is clicked', () => {
    const handleSelect = vi.fn();
    const handleDelete = vi.fn();

    render(
      <SessionSidebar
        sessions={sampleSessions}
        activeSessionId="sess-1"
        onSelectSession={handleSelect}
        onDeleteSession={handleDelete}
        onNewSession={() => {}}
        isOpen={true}
        onToggle={() => {}}
      />
    );

    const deleteButtons = screen.getAllByRole('button', { name: /Delete session/i });
    expect(deleteButtons.length).toBe(2);

    // Click delete on first session
    fireEvent.click(deleteButtons[0]);

    // Verify delete was called with session id
    expect(handleDelete).toHaveBeenCalledWith('sess-1');
    // Verify select was NOT called due to stopPropagation
    expect(handleSelect).not.toHaveBeenCalled();
  });

  it('calls onSelectSession when session item is clicked', () => {
    const handleSelect = vi.fn();

    render(
      <SessionSidebar
        sessions={sampleSessions}
        activeSessionId="sess-1"
        onSelectSession={handleSelect}
        onDeleteSession={() => {}}
        onNewSession={() => {}}
        isOpen={true}
        onToggle={() => {}}
      />
    );

    const sessionItem = screen.getByText('PLG Metrics Exploration');
    fireEvent.click(sessionItem);

    expect(handleSelect).toHaveBeenCalledWith('sess-2');
  });
});
