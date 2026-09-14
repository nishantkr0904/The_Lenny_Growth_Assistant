import React from 'react';

interface MarkdownPreviewProps {
  content: string;
}

export const MarkdownPreview: React.FC<MarkdownPreviewProps> = ({ content }) => {
  return (
    <div className="w-full h-full overflow-y-auto p-6 bg-white">
      <div className="max-w-2xl mx-auto space-y-4 text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap font-sans">
        {content}
      </div>
    </div>
  );
};
