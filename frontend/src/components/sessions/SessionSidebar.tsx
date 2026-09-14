import React from 'react';
import { Session } from '../../types';
import { MessageSquare, Trash2, Plus } from 'lucide-react';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewSession: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const SessionSidebar: React.FC<SessionSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewSession,
  isOpen,
}) => {
  if (!isOpen) {
    return null;
  }

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <aside className="w-64 border-r border-slate-200 bg-slate-50/80 flex flex-col h-full shrink-0 select-none">
      <div className="p-3 border-b border-slate-200 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Research Sessions
        </span>
        <button
          onClick={onNewSession}
          className="p-1 text-slate-500 hover:text-brand-600 hover:bg-white rounded transition"
          title="New Session"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400">
            No sessions yet. Click "New Session" to begin.
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <div
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition ${
                  isActive
                    ? 'bg-white text-slate-900 font-medium shadow-sm border border-slate-200'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center space-x-2 truncate flex-1 mr-2">
                  <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-brand-500' : 'text-slate-400'}`} />
                  <span className="truncate">{session.title || 'Untitled Session'}</span>
                </div>

                <div className="flex items-center space-x-1 shrink-0">
                  <span className="text-[10px] text-slate-400 group-hover:hidden">
                    {formatDate(session.updated_at)}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="hidden group-hover:block p-1 text-slate-400 hover:text-red-500 rounded"
                    title="Delete session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="p-3 border-t border-slate-200 text-[11px] text-slate-400 text-center">
        Corpus: 303 Lenny Transcripts
      </div>
    </aside>
  );
};
