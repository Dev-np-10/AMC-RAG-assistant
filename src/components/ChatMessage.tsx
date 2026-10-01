import { Bot, User, ExternalLink, ShieldAlert, CheckCircle2, Calendar } from 'lucide-react';
import type { ChatMessageData } from '@/types';

interface ChatMessageProps {
  message: ChatMessageData;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 items-start">
        <div className="bg-emerald-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-xl text-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
        <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-emerald-700 text-white flex items-center justify-center">
          <User className="w-5 h-5" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 items-start">
      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
        <Bot className="w-5 h-5" />
      </div>
      <div className="flex-1 space-y-2.5 max-w-2xl">
        <div
          className={`rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed shadow-sm border ${
            message.refused
              ? 'bg-amber-50/70 border-amber-200 text-amber-900'
              : 'bg-white border-slate-200 text-slate-800'
          }`}
        >
          {message.refused && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 mb-2">
              <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>Query Guardrail Activated</span>
            </div>
          )}
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {message.citation && (
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-600 space-y-1.5 hover:border-slate-300 transition-colors">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Official Source Citation</span>
              </div>
              {message.citation.last_updated && (
                <div className="flex items-center gap-1 text-slate-400">
                  <Calendar className="w-3 h-3" />
                  <span>Last updated: {message.citation.last_updated}</span>
                </div>
              )}
            </div>

            <a
              href={message.citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center justify-between gap-2 font-medium text-emerald-700 hover:text-emerald-800"
            >
              <span className="line-clamp-1">{message.citation.title}</span>
              <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 opacity-70 group-hover:opacity-100" />
            </a>

            <div className="text-[11px] text-slate-500">
              {message.citation.amc}
              {message.citation.scheme_name ? ` · ${message.citation.scheme_name}` : ''}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
