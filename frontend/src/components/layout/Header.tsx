import React from 'react';
import { HealthStatus } from '../../types';
import { Cpu, Plus, Sparkles } from 'lucide-react';

interface HeaderProps {
  health: HealthStatus | null;
  onNewSession: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, onNewSession }) => {
  const getProviderBadge = () => {
    if (!health) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
          <span className="w-1.5 h-1.5 mr-1.5 bg-slate-400 rounded-full animate-pulse"></span>
          Checking System...
        </span>
      );
    }

    if (health.status !== 'ok') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
          <span className="w-1.5 h-1.5 mr-1.5 bg-red-500 rounded-full"></span>
          System Degraded
        </span>
      );
    }

    if (health.provider === 'ollama') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-500 rounded-full"></span>
          Ollama (llama3.1:8b)
        </span>
      );
    }

    if (health.provider === 'anthropic') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
          <span className="w-1.5 h-1.5 mr-1.5 bg-purple-500 rounded-full"></span>
          Anthropic (Claude 3.5 Sonnet)
        </span>
      );
    }

    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
        <span className="w-1.5 h-1.5 mr-1.5 bg-blue-500 rounded-full"></span>
        {health.provider}
      </span>
    );
  };

  return (
    <header className="h-14 border-b border-slate-200 bg-white px-4 flex items-center justify-between z-10 shrink-0">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-sm shadow-sm">
          <Sparkles className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm font-semibold text-slate-900 tracking-tight">The Lenny Growth Assistant</h1>
            <span className="text-[10px] font-medium bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">Grounded RAG</span>
          </div>
          <p className="text-[11px] text-slate-500 hidden sm:block">Verified podcast research & Ship 30 for 30 synthesis</p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="hidden md:flex items-center space-x-2">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs text-slate-500">Active Provider:</span>
          {getProviderBadge()}
        </div>

        <button
          onClick={onNewSession}
          className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-brand-500 hover:bg-brand-600 active:bg-brand-700 rounded-md shadow-sm transition-colors"
          aria-label="Create new research session"
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          <span>New Session</span>
        </button>
      </div>
    </header>
  );
};
