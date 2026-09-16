import React from 'react';
import { Info } from 'lucide-react';

interface RefusalCardProps {
  content: string;
}

export const RefusalCard: React.FC<RefusalCardProps> = ({ content }) => {
  return (
    <div className="rounded-lg border border-amber-200 dark:border-amber-800/60 bg-[#FEF9EF] dark:bg-amber-950/30 p-4 text-xs text-amber-900 dark:text-amber-200 shadow-sm space-y-2 transition-colors">
      <div className="flex items-center space-x-2 font-medium text-amber-800 dark:text-amber-300">
        <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
        <span className="uppercase tracking-wider text-[10px] font-semibold">Insufficient Corpus Evidence</span>
      </div>
      <p className="leading-relaxed text-amber-950 dark:text-amber-100 whitespace-pre-wrap">{content}</p>
      <div className="text-[11px] text-amber-700/80 dark:text-amber-400/80 pt-1 border-t border-amber-200/60 dark:border-amber-800/50">
        The Grounding Gate refused this query because it is not covered in Lenny's Podcast transcripts. Zero ungrounded speculation is permitted.
      </div>
    </div>
  );
};
