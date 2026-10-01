import { useState, useRef, useEffect, useCallback } from 'react';
import { Bot, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import type { ChatMessageData, RagResponse } from '@/types';
import { askQuestion } from '@/lib/api';
import { checkGuardrails } from '@/lib/guardrails';
import { demoSearch, EXAMPLE_QUESTIONS, AMC_NAME } from '@/lib/demoKnowledge';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { SourcePanel } from '@/components/SourcePanel';

let msgIdCounter = 0;
function nextId(): string {
  msgIdCounter += 1;
  return `msg-${msgIdCounter}`;
}

function App() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleAsk = useCallback(async (question: string) => {
    setError(null);

    const userMsg: ChatMessageData = {
      id: nextId(),
      role: 'user',
      content: question,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const guardrail = checkGuardrails(question);
      let response: RagResponse;

      if (guardrail.blocked) {
        response = {
          answer: guardrail.reason,
          citation: null,
          last_updated: null,
          refused: true,
          refusal_reason: guardrail.reason,
        };
      } else {
        try {
          response = await askQuestion(question);
        } catch {
          response = demoSearch(question);
        }
      }

      const assistantMsg: ChatMessageData = {
        id: nextId(),
        role: 'assistant',
        content: response.answer,
        citation: response.citation ?? undefined,
        lastUpdated: response.last_updated ?? undefined,
        refused: response.refused,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center">
          <Bot className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-slate-800 leading-tight">Facts-Only Mutual Fund Chatbot</h1>
          <p className="text-xs text-slate-500">{AMC_NAME} · Powered by RAG + pgvector</p>
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
          <Sparkles className="w-3.5 h-3.5" />
          <span className="font-medium">Facts Only</span>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                  <Bot className="w-9 h-9" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-800">Ask factual questions about HDFC mutual funds</h2>
                  <p className="text-sm text-slate-500 mt-1 max-w-md">
                    I answer only factual questions about expense ratio, SIP, exit load, lock-in, riskometer, and benchmark.
                    No investment advice. No personal information.
                  </p>
                </div>
                <div className="flex flex-col gap-2 w-full max-w-lg mt-2">
                  {EXAMPLE_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => handleAsk(q)}
                      disabled={loading}
                      className="text-left text-sm bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-700 hover:border-emerald-300 hover:bg-emerald-50/50 transition-colors disabled:opacity-50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <Bot className="w-5 h-5" />
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                  <Loader2 className="w-5 h-5 text-emerald-600 animate-spin" />
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Disclaimer */}
          <div className="px-4 py-2 bg-amber-50 border-t border-amber-200">
            <p className="text-xs text-amber-800 leading-relaxed">
              <strong>Disclaimer:</strong> This chatbot provides factual information from official sources only.
              It does not give investment advice or recommendations. Always consult a SEBI-registered financial advisor before investing.
            </p>
          </div>

          {/* Input */}
          <div className="px-4 py-3 bg-white border-t border-slate-200">
            <ChatInput onSend={handleAsk} disabled={loading} />
          </div>

          {/* Sources panel */}
          <SourcePanel />
        </div>
      </div>
    </div>
  );
}

export default App;
