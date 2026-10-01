export interface Citation {
  source_id: string;
  title: string;
  url: string;
  amc: string;
  scheme_name: string;
  last_updated: string;
}

export interface RagResponse {
  answer: string;
  citation: Citation | null;
  last_updated: string | null;
  refused: boolean;
  refusal_reason?: string | null;
  category?: string;
}

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citation?: Citation;
  lastUpdated?: string;
  refused?: boolean;
  timestamp: number;
}

export interface SourceItem {
  source_id: string;
  amc: string;
  scheme_name: string | null;
  source_type: string;
  url: string;
  title: string;
  last_updated: string | null;
}
