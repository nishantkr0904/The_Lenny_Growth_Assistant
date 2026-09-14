import React from 'react';
import { Info } from 'lucide-react';

interface RefusalCardProps {
  content: string;
}

export const RefusalCard: React.FC<RefusalCardProps> = ({ content }) => {
  return (
    <div className="rounded-lg border border-amber-200 bg-[#FEF9EF] p-4 text-xs text-amber-900 shadow-sm space-y-2">
      <div className="flex items-center space-x-2 font-medium text-amber-800">
        <Info className="w-4 h-4 text-amber-600 shrink-0" />
        <span className="uppercase tracking-wider text-[10px] font-semibold">Insufficient Corpus Evidence</span>
      </div>
      <p className="leading-relaxed text-amber-950 whitespace-pre-wrap">{content}</p>
      <div className="text-[11px] text-amber-700/80 pt-1 border-t border-amber-200/60">
        The Grounding Gate refused this query because it is not covered in Lenny's Podcast transcripts. Zero ungrounded speculation is permitted.
      </div>
    </div>
  );
};
