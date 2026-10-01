export type ChatRole = 'user' | 'assistant';

export interface Citation {
  source_id: string;
  title: string;
  url: string;
  amc: string;
  scheme_name: string;
  last_updated: string;
}

export interface ChatMessageData {
  id: string;
  role: ChatRole;
  content: string;
  citation?: Citation;
  lastUpdated?: string;
  refused?: boolean;
  timestamp: number;
}

export interface RagResponse {
  answer: string;
  citation: Citation | null;
  last_updated: string | null;
  refused: boolean;
  refusal_reason?: string;
}

export interface FundSource {
  source_id: string;
  amc: string;
  scheme_name: string;
  source_type: string;
  url: string;
  title: string;
  last_updated: string | null;
}
