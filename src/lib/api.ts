import type { RagResponse } from '@/types';
import { demoSearch, DEMO_SOURCES } from '@/lib/demoKnowledge';

const API_BASE = (import.meta.env.VITE_API_BASE as string) || '';

export async function askQuestion(question: string): Promise<RagResponse> {
  if (!API_BASE) {
    return demoSearch(question);
  }

  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => '');
    throw new Error(`Request failed (${response.status}). ${errorBody}`);
  }

  const data = await response.json();

  if (!data || typeof data.answer !== 'string') {
    throw new Error('Unexpected response format from server.');
  }

  return {
    answer: data.answer,
    citation: data.citation ?? null,
    last_updated: data.last_updated ?? null,
    refused: data.refused ?? false,
    refusal_reason: data.refusal_reason,
  };
}

export async function fetchSources(): Promise<
  Array<{ source_id: string; amc: string; scheme_name: string; source_type: string; url: string; title: string; last_updated: string | null }>
> {
  if (!API_BASE) {
    return DEMO_SOURCES;
  }

  try {
    const response = await fetch(`${API_BASE}/api/sources`);
    if (!response.ok) return DEMO_SOURCES;
    const data = await response.json();
    if (!Array.isArray(data)) return DEMO_SOURCES;
    return data;
  } catch {
    return DEMO_SOURCES;
  }
}

export async function checkHealth(): Promise<{ status: string; openai_configured: boolean; supabase_configured: boolean; date: string } | null> {
  if (!API_BASE) {
    return {
      status: 'ok',
      openai_configured: false,
      supabase_configured: false,
      date: new Date().toISOString().split('T')[0],
    };
  }

  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}
