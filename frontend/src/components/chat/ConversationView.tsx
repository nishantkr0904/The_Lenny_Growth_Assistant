import React, { useEffect, useRef } from 'react';
import { Message, SourceReference } from '../../types';
import { AnswerBlock } from './AnswerBlock';
import { Bot, User, Sparkles, Loader2 } from 'lucide-react';

interface ConversationViewProps {
  messages: Message[];
  isLoading: boolean;
  statusText?: string;
  onOpenSources: (sources: SourceReference[]) => void;
  onCreateArtifact: (message: Message) => void;
  onSelectPrompt: (prompt: string) => void;
}

const EXAMPLE_PROMPTS = [
  {
    title: 'Ada Chen Rekhi on Career Stagnation',
    query: 'According to Ada Chen Rekhi, what should you do when you feel stuck or like a boiling frog in your career?',
  },
  {
    title: 'Explore vs. Exploit Mode',
    query: 'What did Ada Chen Rekhi say about career exploration vs exploitation?',
  },
  {
    title: 'Test Deterministic Refusal',
    query: 'According to the Lenny Podcast transcripts, what is quantum chromodynamics in lattice gauge theory?',
  },
];

export const ConversationView: React.FC<ConversationViewProps> = ({
  messages,
  isLoading,
  statusText,
  onOpenSources,
  onCreateArtifact,
  onSelectPrompt,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, statusText]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4 sm:p-8 flex flex-col items-center justify-center text-center">
        <div className="max-w-md space-y-6">
          <div className="w-12 h-12 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto shadow-xs border border-brand-100">
            <Sparkles className="w-6 h-6" />
          </div>

          <div className="space-y-1.5">
            <h2 className="text-base font-semibold text-slate-800">
              Grounded Growth & Strategy Research
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every factual assertion is strictly retrieved from Lenny Rachitsky's podcast interviews with top operators and leaders.
            </p>
          </div>

          <div className="space-y-2 pt-2 text-left">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider pl-1">
              Suggested Research Questions
            </span>
            {EXAMPLE_PROMPTS.map((item, idx) => (
              <button
                key={idx}
                onClick={() => onSelectPrompt(item.query)}
                className="w-full p-3 rounded-lg border border-slate-200 hover:border-brand-300 bg-white hover:bg-brand-50/40 text-left transition shadow-2xs group"
              >
                <div className="text-xs font-medium text-slate-800 group-hover:text-brand-700">
                  {item.title}
                </div>
                <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                  "{item.query}"
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
      <div className="max-w-4xl mx-auto space-y-5">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-7 h-7 rounded-lg bg-brand-500 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-[80%] rounded-xl p-4 text-xs sm:text-sm shadow-xs ${
                  isUser
                    ? 'bg-slate-900 text-white rounded-br-xs'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-xs'
                }`}
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                ) : (
                  <AnswerBlock
                    message={msg}
                    onOpenSources={onOpenSources}
                    onCreateArtifact={onCreateArtifact}
                  />
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {/* Loading Progress State */}
        {isLoading && statusText && (
          <div className="flex items-center space-x-3 text-xs text-slate-500 pl-1 py-1">
            <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
              <Loader2 className="w-3.5 h-3.5 text-brand-500 animate-spin" />
            </div>
            <span className="italic">{statusText}</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
