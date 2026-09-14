import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ComposerProps {
  onSendMessage: (content: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const Composer: React.FC<ComposerProps> = ({ onSendMessage, isLoading, disabled = false }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;

    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  return (
    <div className="p-3 sm:p-4 bg-white border-t border-slate-200">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex items-end space-x-2">
        <div className="flex-1 relative rounded-lg border border-slate-300 focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500 bg-white transition shadow-2xs">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            placeholder="Ask a question grounded in Lenny's Podcast transcripts..."
            className="w-full resize-none bg-transparent px-3 py-2.5 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none max-h-44 min-h-[44px]"
            aria-label="Ask a research question"
          />
        </div>

        <button
          type="submit"
          disabled={!input.trim() || isLoading || disabled}
          className={`h-11 px-4 rounded-lg flex items-center justify-center font-medium text-xs sm:text-sm text-white transition shadow-sm shrink-0 ${
            !input.trim() || isLoading || disabled
              ? 'bg-slate-300 cursor-not-allowed text-slate-500'
              : 'bg-brand-500 hover:bg-brand-600 active:bg-brand-700'
          }`}
          aria-label="Send message"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>
    </div>
  );
};
