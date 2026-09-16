import React from 'react';
import { SourceReference } from '../../types';
import { BookOpen } from 'lucide-react';

interface CitationBadgeProps {
  index: number;
  source: SourceReference;
  onClick: (source: SourceReference) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ index, source, onClick }) => {
  return (
    <button
      type="button"
      onClick={() => onClick(source)}
      className="inline-flex items-center space-x-1 px-2 py-0.5 m-0.5 rounded-full text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-brand-50 dark:hover:bg-brand-950/50 hover:text-brand-700 dark:hover:text-brand-300 border border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-700 transition shadow-2xs"
      title={`Inspect source quote from ${source.guest} (${source.title})`}
      aria-label={`Citation ${index}: ${source.guest}`}
    >
      <BookOpen className="w-3 h-3 text-slate-400 group-hover:text-brand-500" />
      <span>
        [{index}] {source.guest || 'Lenny Guest'}
      </span>
    </button>
  );
};
