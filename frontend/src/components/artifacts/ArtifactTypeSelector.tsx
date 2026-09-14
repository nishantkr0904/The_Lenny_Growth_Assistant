import React, { useState } from 'react';
import { PenTool, FileText, Code, X, Sparkles, Loader2 } from 'lucide-react';

interface ArtifactTypeSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (type: 'ship30_essay' | 'markdown' | 'html_card', title: string) => void;
  isLoading: boolean;
  defaultTitle?: string;
}

export const ArtifactTypeSelector: React.FC<ArtifactTypeSelectorProps> = ({
  isOpen,
  onClose,
  onGenerate,
  isLoading,
  defaultTitle = 'Strategic Growth Playbook',
}) => {
  const [selectedType, setSelectedType] = useState<'ship30_essay' | 'markdown' | 'html_card'>('ship30_essay');
  const [title, setTitle] = useState(defaultTitle);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate(selectedType, title || 'Growth Research Artifact');
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-brand-500" />
            <h3 className="text-sm font-semibold text-slate-900">Transform Insight into Artifact</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded"
            disabled={isLoading}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-slate-700">Artifact Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
              placeholder="e.g. Navigating Explore vs Exploit"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-700">Select Artifact Format</label>
            <div className="space-y-2">
              {/* Ship 30 Option */}
              <div
                onClick={() => !isLoading && setSelectedType('ship30_essay')}
                className={`p-3 rounded-lg border cursor-pointer transition flex items-start space-x-3 ${
                  selectedType === 'ship30_essay'
                    ? 'border-brand-500 bg-brand-50/40 ring-1 ring-brand-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-7 h-7 rounded-md bg-brand-100 text-brand-700 flex items-center justify-center shrink-0 mt-0.5">
                  <PenTool className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-900 flex items-center space-x-1.5">
                    <span>Essay (Ship 30 for 30)</span>
                    <span className="text-[10px] bg-brand-100 text-brand-700 px-1.5 py-0.2 rounded font-normal">Recommended</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
                    ~1,250-word atomic essay encoding the 7 Ship 30 principles: Grabber hook, 4A narrative, skimmable headings, and tactical takeaways grounded in Lenny's guests.
                  </p>
                </div>
              </div>

              {/* Research Brief Markdown Option */}
              <div
                onClick={() => !isLoading && setSelectedType('markdown')}
                className={`p-3 rounded-lg border cursor-pointer transition flex items-start space-x-3 ${
                  selectedType === 'markdown'
                    ? 'border-brand-500 bg-brand-50/40 ring-1 ring-brand-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-7 h-7 rounded-md bg-slate-100 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-900">Research Brief (Markdown)</div>
                  <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
                    Structured research notes with headings, strategic insights, framework bullets, and source footnotes. Ready to paste into docs.
                  </p>
                </div>
              </div>

              {/* HTML Card Option */}
              <div
                onClick={() => !isLoading && setSelectedType('html_card')}
                className={`p-3 rounded-lg border cursor-pointer transition flex items-start space-x-3 ${
                  selectedType === 'html_card'
                    ? 'border-brand-500 bg-brand-50/40 ring-1 ring-brand-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-7 h-7 rounded-md bg-slate-100 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <Code className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-900">Visual Artifact (HTML/CSS)</div>
                  <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
                    Styled, self-contained HTML card rendered with custom typography and strict Content Security Policy.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 rounded-md transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center px-4 py-1.5 text-xs font-medium text-white bg-brand-500 hover:bg-brand-600 rounded-md shadow-sm transition disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  <span>Compiling Artifact...</span>
                </>
              ) : (
                <span>Generate Artifact</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
