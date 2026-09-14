import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../components/layout/Header';
import { EvidenceIndicator } from '../components/chat/EvidenceIndicator';
import { RefusalCard } from '../components/chat/RefusalCard';
import { CitationBadge } from '../components/chat/CitationBadge';
import { SourceDrawer } from '../components/chat/SourceDrawer';
import { SafeHtmlPreview } from '../components/artifacts/SafeHtmlPreview';
import { ArtifactViewer } from '../components/artifacts/ArtifactViewer';
import { Artifact, HealthStatus, SourceReference } from '../types';

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
});

describe('Grounding Trust UX Components', () => {
  it('renders EvidenceIndicator correctly for Strong, Limited, and Conflicting tiers', () => {
    const { rerender } = render(<EvidenceIndicator tier="strong" sourcesCount={2} />);
    expect(screen.getByText(/Strong Evidence · 2 sources/i)).toBeInTheDocument();

    rerender(<EvidenceIndicator tier="limited" sourcesCount={1} />);
    expect(screen.getByText(/Limited Evidence · 1 source/i)).toBeInTheDocument();

    rerender(<EvidenceIndicator tier="conflicting" sourcesCount={3} />);
    expect(screen.getByText(/Contrasting Perspectives · 3 sources/i)).toBeInTheDocument();
  });

  it('renders RefusalCard for Insufficient evidence with zero hallucinations', () => {
    const refusalText = 'I could not find guidance on this topic in Lenny\'s Podcast transcripts.';
    render(<RefusalCard content={refusalText} />);
    expect(screen.getByText(/Insufficient Corpus Evidence/i)).toBeInTheDocument();
    expect(screen.getByText(refusalText)).toBeInTheDocument();
    expect(screen.getByText(/Zero ungrounded speculation is permitted/i)).toBeInTheDocument();
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
