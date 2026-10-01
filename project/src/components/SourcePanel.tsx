import { useState } from 'react';
import { ChevronDown, ChevronUp, Database, Info, ListChecks, BookOpen } from 'lucide-react';
import { DEMO_SOURCES, SCHEMES, AMC_NAME } from '@/lib/demoKnowledge';

export function SourcePanel() {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-t border-slate-200 bg-slate-50">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Database className="w-4 h-4" />
          Ingested Sources ({DEMO_SOURCES.length})
        </span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 max-h-80 overflow-y-auto">
          <div className="bg-white rounded-lg border border-slate-200 p-3">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" /> AMC & Schemes
            </h4>
            <p className="text-sm text-slate-700 font-medium">{AMC_NAME}</p>
            <ul className="mt-1.5 space-y-1">
              {SCHEMES.map((s) => (
                <li key={s} className="text-sm text-slate-600 flex items-start gap-1.5">
                  <span className="text-emerald-500 mt-0.5">•</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5" /> Official Sources
            </h4>
            <div className="space-y-1.5">
              {DEMO_SOURCES.map((src) => (
                <a
                  key={src.source_id}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block bg-white rounded-md border border-slate-200 px-3 py-2 hover:border-emerald-300 hover:bg-emerald-50/50 transition-colors"
                >
                  <p className="text-sm text-slate-700 font-medium leading-snug">{src.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {src.amc} {src.scheme_name ? `· ${src.scheme_name}` : ''} · {src.source_type}
                  </p>
                </a>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-3">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <ListChecks className="w-3.5 h-3.5" /> Answer Policy
            </h4>
            <ul className="space-y-1 text-xs text-slate-600">
              <li>• Only factual questions about covered schemes</li>
              <li>• Maximum 3 sentences per answer</li>
              <li>• Exactly one official citation per answer</li>
              <li>• No investment advice or predictions</li>
              <li>• No personal information (PAN, Aadhaar, OTP, etc.)</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
