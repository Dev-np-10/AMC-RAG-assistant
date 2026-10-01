import type { ChatMessageData } from '@/types';
import { User, Bot, ExternalLink, ShieldAlert, FileText } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageData;
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center ${
          isUser
            ? 'bg-slate-700 text-white'
            : message.refused
              ? 'bg-amber-100 text-amber-700'
              : 'bg-emerald-100 text-emerald-700'
        }`}
      >
        {isUser ? <User className="w-5 h-5" /> : message.refused ? <ShieldAlert className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      <div className={`flex flex-col gap-1.5 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'bg-slate-700 text-white rounded-tr-sm'
              : message.refused
                ? 'bg-amber-50 text-amber-900 border border-amber-200 rounded-tl-sm'
                : 'bg-white text-slate-800 border border-slate-200 rounded-tl-sm shadow-sm'
          }`}
        >
          <p>{message.content}</p>
        </div>

        {!isUser && message.citation && (
          <a
            href={message.citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-emerald-700 hover:text-emerald-800 hover:underline bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200 transition-colors"
          >
            <FileText className="w-3 h-3" />
            <span className="font-medium">{message.citation.title}</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {!isUser && message.lastUpdated && (
          <p className="text-xs text-slate-400 px-1">
            Last updated from sources: {formatDate(message.lastUpdated)}
          </p>
        )}
      </div>
    </div>
  );
}
