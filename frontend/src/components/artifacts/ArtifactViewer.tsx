import React, { useState } from 'react';
import { Artifact } from '../../types';
import { SafeHtmlPreview } from './SafeHtmlPreview';
import { MarkdownPreview } from './MarkdownPreview';
import { X, Copy, Download, Check, Eye, Code2, ShieldAlert, Sparkles } from 'lucide-react';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onClose: () => void;
  isOpen: boolean;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact, onClose, isOpen }) => {
  const [viewMode, setViewMode] = useState<'preview' | 'source'>('preview');
  const [copied, setCopied] = useState(false);

  if (!isOpen || !artifact) return null;

  const isHtml = artifact.artifact_type === 'html_card' || !!artifact.content_html;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content_raw || artifact.content_html || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy artifact:', err);
    }
  };

  const handleDownload = () => {
    const ext = isHtml && viewMode === 'source' ? 'html' : 'md';
    const blob = new Blob([artifact.content_raw || artifact.content_html || ''], {
      type: ext === 'html' ? 'text/html' : 'text/markdown',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <aside className="w-full md:w-[480px] lg:w-[580px] xl:w-[680px] border-l border-slate-200 bg-white flex flex-col h-full shadow-xl z-20 shrink-0">
      {/* Viewer Header */}
      <div className="p-3 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center space-x-2 truncate mr-2">
          <Sparkles className="w-4 h-4 text-brand-500 shrink-0" />
          <h2 className="text-xs font-semibold text-slate-800 truncate" title={artifact.title}>
            {artifact.title}
          </h2>
          <span className="text-[10px] bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded font-medium shrink-0 uppercase tracking-wider">
            {artifact.artifact_type.replace('_', ' ')}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 shrink-0">
          {/* View Mode Toggle */}
          <div className="flex bg-slate-200/80 p-0.5 rounded-lg text-[11px] font-medium">
            <button
              onClick={() => setViewMode('preview')}
              className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1 ${
                viewMode === 'preview'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Eye className="w-3 h-3" />
              <span>Preview</span>
            </button>
            <button
              onClick={() => setViewMode('source')}
              className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1 ${
                viewMode === 'source'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Code2 className="w-3 h-3" />
              <span>Source</span>
            </button>
          </div>

          <button
            onClick={handleCopy}
            className="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-md transition"
            title="Copy to clipboard"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
          </button>

          <button
            onClick={handleDownload}
            className="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-md transition"
            title="Download file"
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-md transition"
            title="Close viewer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Trust & Isolation Boundary */}
      <div className="px-3 py-1.5 bg-slate-100/70 border-b border-slate-200 text-[10px] text-slate-500 flex items-center justify-between">
        <div className="flex items-center space-x-1.5">
          <ShieldAlert className="w-3 h-3 text-slate-400" />
          <span>Generated Content · Sandboxed Execution (Null Origin · No Script Permissions)</span>
        </div>
        <span>Sources: {artifact.sources?.length || 0}</span>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative bg-slate-50">
        {viewMode === 'preview' ? (
          isHtml ? (
            <SafeHtmlPreview htmlContent={artifact.content_html!} />
          ) : (
            <MarkdownPreview content={artifact.content_raw} />
          )
        ) : (
          <div className="w-full h-full overflow-y-auto p-4 bg-slate-900 text-slate-100 font-mono text-xs leading-relaxed">
            <pre className="whitespace-pre-wrap">{artifact.content_raw || artifact.content_html}</pre>
          </div>
        )}
      </div>
    </aside>
  );
};
