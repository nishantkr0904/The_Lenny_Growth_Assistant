import React from 'react';
import { SourceReference } from '../../types';
import { SourceCard } from './SourceCard';
import { X, Database, ShieldCheck } from 'lucide-react';

interface SourceDrawerProps {
  sources: SourceReference[];
  onClose: () => void;
  isOpen: boolean;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({ sources, onClose, isOpen }) => {
  if (!isOpen) return null;

  return (
    <aside className="w-80 md:w-96 border-l border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 flex flex-col h-full shadow-lg z-20 shrink-0 transition-colors">
      <div className="p-3.5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="w-4 h-4 text-brand-500" />
          <h2 className="text-xs font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
            Verified Transcript Evidence
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded transition"
          aria-label="Close source inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-3 bg-brand-50/50 dark:bg-brand-950/40 border-b border-brand-100 dark:border-brand-900 text-[11px] text-brand-800 dark:text-brand-300 flex items-center space-x-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400 shrink-0" />
        <span>Validated via P0.3 pgvector cosine retrieval & GroundingGate</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {sources.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400 dark:text-slate-500">
            No source citations attached to this turn.
          </div>
        ) : (
          sources.map((src, idx) => (
            <SourceCard key={src.chunk_id || idx} source={src} index={idx + 1} />
          ))
        )}
      </div>
    </aside>
  );
};
