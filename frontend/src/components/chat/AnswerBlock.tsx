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
      <div className="prose prose-slate dark:prose-invert max-w-none text-xs sm:text-sm leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-wrap">
        {message.content}
        {message.isStreaming && (
          <span className="inline-block w-1.5 h-4 ml-1 bg-brand-500 animate-pulse align-middle" />
        )}
      </div>

      {/* Citation Badges */}
      {sources.length > 0 && (
        <div className="pt-2 border-t border-slate-100 dark:border-slate-700 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500 mr-1 flex items-center">
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
            className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-950/60 hover:bg-brand-100 dark:hover:bg-brand-900/60 border border-brand-200 dark:border-brand-800 rounded-md transition shadow-2xs"
            title="Transform insight into a Ship 30 essay, Markdown brief, or HTML card"
          >
            <PenTool className="w-3.5 h-3.5 mr-1 text-brand-600 dark:text-brand-400" />
            <span>Create Artifact</span>
          </button>

          <button
            onClick={() => onOpenSources(sources)}
            className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-md transition"
          >
            <span>View All Sources ({sources.length})</span>
          </button>
        </div>
      )}
    </div>
  );
};
