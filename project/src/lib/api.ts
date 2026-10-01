import type { RagResponse } from '@/types';

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000';

export async function askQuestion(question: string): Promise<RagResponse> {
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
  try {
    const response = await fetch(`${API_BASE}/api/sources`);
    if (!response.ok) return [];
    const data = await response.json();
    if (!Array.isArray(data)) return [];
    return data;
  } catch {
    return [];
  }
}

export async function checkHealth(): Promise<{ status: string; openai_configured: boolean; supabase_configured: boolean; date: string } | null> {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}
