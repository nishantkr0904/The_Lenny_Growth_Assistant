import React from 'react';
import { Message, SourceReference } from '../../types';
import { EvidenceIndicator } from './EvidenceIndicator';
import { CitationBadge } from './CitationBadge';
import { RefusalCard } from './RefusalCard';
import { PenTool, Database } from 'lucide-react';

interface AnswerBlockProps {
  message: Message;
  onOpenSources: (sources: SourceReference[]) => void;
  onCreateArtifact: (message: Message) => void;
}

export const AnswerBlock: React.FC<AnswerBlockProps> = ({
  message,
  onOpenSources,
  onCreateArtifact,
}) => {
  const normalizedTier = message.evidence_tier?.toLowerCase();
  const isInsufficient = normalizedTier === 'insufficient';
  const sources = message.sources || [];

  if (isInsufficient) {
    return <RefusalCard content={message.content} />;
  }

  return (
    <div className="space-y-3">
      {/* Evidence Quality Header */}
      <div className="flex items-center justify-between">
        <EvidenceIndicator tier={message.evidence_tier} sourcesCount={sources.length} />
        {message.latency_ms && (
          <span className="text-[10px] text-slate-400 font-mono">
            {message.latency_ms}ms
          </span>
        )}
      </div>

      {/* Main Content Body */}
      <div className="prose prose-slate max-w-none text-xs sm:text-sm leading-relaxed text-slate-800 whitespace-pre-wrap">
        {message.content}
        {message.isStreaming && (
          <span className="inline-block w-1.5 h-4 ml-1 bg-brand-500 animate-pulse align-middle" />
        )}
      </div>

      {/* Citation Badges */}
      {sources.length > 0 && (
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-slate-400 mr-1 flex items-center">
            <Database className="w-3 h-3 mr-1" /> Sources:
          </span>
          {sources.map((src, idx) => (
            <CitationBadge
              key={src.chunk_id || idx}
              index={idx + 1}
              source={src}
              onClick={() => onOpenSources(sources)}
            />
          ))}
        </div>
      )}

      {/* Artifact Action Bar - only render for valid, non-refusal answers with evidence */}
      {!message.isStreaming && message.content && !isInsufficient && sources.length > 0 && (
        <div className="pt-2 flex items-center space-x-2">
          <button
            onClick={() => onCreateArtifact(message)}
            className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 rounded-md transition shadow-2xs"
            title="Transform insight into a Ship 30 essay, Markdown brief, or HTML card"
          >
            <PenTool className="w-3.5 h-3.5 mr-1 text-brand-600" />
            <span>Create Artifact</span>
          </button>

          <button
            onClick={() => onOpenSources(sources)}
            className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-md transition"
          >
            <span>View All Sources ({sources.length})</span>
          </button>
        </div>
      )}
    </div>
  );
};
