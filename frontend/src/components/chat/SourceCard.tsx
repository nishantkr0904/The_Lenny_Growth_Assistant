import React from 'react';
import { SourceReference } from '../../types';
import { Quote } from 'lucide-react';

interface SourceCardProps {
  source: SourceReference;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index }) => {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs space-y-2">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center space-x-1.5">
            <span className="text-xs font-bold text-slate-900">[{index}] {source.guest || 'Podcast Guest'}</span>
            {source.similarity_score && (
              <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                {Math.round(source.similarity_score * 100)}% match
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-500 line-clamp-1 italic mt-0.5">
            {source.title || "Lenny's Podcast"}
          </p>
        </div>
      </div>

      <div className="bg-slate-50 rounded p-2.5 border-l-2 border-brand-500 text-xs text-slate-700 leading-relaxed italic">
        <Quote className="w-3 h-3 text-brand-400 mb-1 inline mr-1" />
        "{source.quoted_excerpt || 'Verbatim transcript dialogue retrieved from PostgreSQL pgvector.'}"
      </div>
    </div>
  );
};
