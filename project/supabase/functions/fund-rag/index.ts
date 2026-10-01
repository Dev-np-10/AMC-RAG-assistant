import { createClient } from 'npm:@supabase/supabase-js@2.57.4';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Client-Info, Apikey',
};

interface Citation {
  source_id: string;
  title: string;
  url: string;
  amc: string;
  scheme_name: string;
  last_updated: string;
}

interface RagResult {
  answer: string;
  citation: Citation | null;
  last_updated: string | null;
  refused: boolean;
  refusal_reason?: string;
}

// ── Guardrails ──────────────────────────────────────────────

const PII_PATTERNS = [
  /[A-Z]{5}\d{4}[A-Z]/,
  /\d{12}/,
  /\d{4}\s?\d{4}\s?\d{4}/,
  /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
  /\d{10}/,
  /\b\d{6}\b/,
  /\b(?:\+\d{1,3}[-\s]?)?\d{10}\b/,
  /(?:PAN|Aadhaar|OTP|account\s*(?:number|no)?)/i,
];

const ADVICE_PATTERNS = [
  /should\s+i\s*(?:invest|buy|sell|redeem|switch)/i,
  /which\s*(?:fund|scheme)\s*(?:should|to)\s*(?:i\s*)?(?:invest|buy|choose)/i,
  /is\s*(?:it|this)\s*(?:a\s*)?(?:good|bad)\s*(?:time|investment)/i,
  /recommend/i,
  /best\s*(?:fund|scheme|investment)/i,
  /will\s*(?:the\s*)?(?:nav|return|fund)\s*(?:go|be|increase|decrease)/i,
  /predict/i,
  /future\s*(?:return|performance|nav)/i,
  /compare\s*(?:the\s*)?(?:return|performance|nav)/i,
  /which\s*is\s*better/i,
  /should\s*i\s*(?:hold|exit|continue)/i,
  /portfolio\s*(?:allocation|recommendation|suggestion)/i,
  /how\s*(?:much|should)\s*i\s*invest/i,
  /is\s*(?:hdfc|this)\s*(?:fund|scheme)\s*(?:safe|good|bad)/i,
];

function checkGuardrails(question: string): { blocked: boolean; reason: string } {
  for (const p of PII_PATTERNS) {
    if (p.test(question)) {
      return {
        blocked: true,
        reason: 'Your question appears to contain sensitive personal information (PAN, Aadhaar, OTP, phone, email, or account details). For your security, I cannot process questions containing PII. Please rephrase your question without personal details.',
      };
    }
  }
  for (const p of ADVICE_PATTERNS) {
    if (p.test(question)) {
      return {
        blocked: true,
        reason: 'I am a facts-only chatbot and cannot provide investment advice, recommendations, return predictions, or comparisons. I can only answer factual questions about expense ratio, SIP, exit load, lock-in period, riskometer, benchmark, and scheme statements from official sources.',
      };
    }
  }
  return { blocked: false, reason: '' };
}

// ── OpenAI helpers ───────────────────────────────────────────

async function getEmbedding(text: string, apiKey: string): Promise<number[] | null> {
  try {
    const res = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'text-embedding-3-small',
        input: text,
      }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data?.data?.[0]?.embedding ?? null;
  } catch {
    return null;
  }
}

async function getLLMAnswer(
  question: string,
  context: string,
  citationTitle: string,
  apiKey: string
): Promise<string | null> {
  const systemPrompt = `You are a facts-only mutual fund chatbot. Answer the user's question using ONLY the provided context from official sources. Rules:
1. Answer in 3 sentences or fewer.
2. State only facts from the context — no opinions, advice, or predictions.
3. Do not compare funds or recommend investments.
4. If the context does not contain the answer, say "I could not find this information in the available sources."
5. Do not mention the context or source by name in the answer — just state the facts.`;

  try {
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          { role: 'system', content: systemPrompt },
          {
            role: 'user',
            content: `Context from ${citationTitle}:\n\n${context}\n\nQuestion: ${question}`,
          },
        ],
        temperature: 0,
        max_tokens: 150,
      }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data?.choices?.[0]?.message?.content ?? null;
  } catch {
    return null;
  }
}

// ── Main handler ─────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const { question } = await req.json();
    if (typeof question !== 'string' || !question.trim()) {
      return new Response(
        JSON.stringify({ error: 'Question is required.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Guardrails
    const guardrail = checkGuardrails(question);
    if (guardrail.blocked) {
      const result: RagResult = {
        answer: guardrail.reason,
        citation: null,
        last_updated: null,
        refused: true,
        refusal_reason: guardrail.reason,
      };
      return new Response(JSON.stringify(result), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
    const openaiKey = Deno.env.get('OPENAI_API_KEY') ?? '';

    const supabase = createClient(supabaseUrl, serviceKey);

    // Generate embedding
    const embedding = await getEmbedding(question, openaiKey);

    let chunks: Array<{
      id: string;
      source_id: string;
      chunk_index: number;
      content: string;
      metadata: Record<string, unknown>;
      similarity: number;
    }> = [];

    if (embedding) {
      const { data, error } = await supabase.rpc('match_fund_chunks', {
        query_embedding: embedding,
        match_count: 5,
      });
      if (!error && data) {
        chunks = data;
      }
    }

    // If no chunks found (no embeddings ingested yet), return "not found"
    if (chunks.length === 0) {
      const result: RagResult = {
        answer: 'I could not find any factual information about this in the ingested sources. Please try asking about expense ratio, SIP, exit load, lock-in period, riskometer, or benchmark for any of the four HDFC schemes covered.',
        citation: null,
        last_updated: null,
        refused: false,
      };
      return new Response(JSON.stringify(result), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Get source metadata for the top chunk
    const topChunk = chunks[0];
    const { data: sourceData } = await supabase
      .from('fund_sources')
      .select('source_id, title, url, amc, scheme_name, last_updated')
      .eq('source_id', topChunk.source_id)
      .maybeSingle();

    const citation: Citation | null = sourceData
      ? {
          source_id: sourceData.source_id,
          title: sourceData.title,
          url: sourceData.url,
          amc: sourceData.amc,
          scheme_name: sourceData.scheme_name ?? '',
          last_updated: sourceData.last_updated ?? '',
        }
      : null;

    // Build context from top chunks
    const contextText = chunks
      .slice(0, 3)
      .map((c) => c.content)
      .join('\n\n');

    // Get LLM answer
    let answer: string | null = null;
    if (openaiKey && citation) {
      answer = await getLLMAnswer(question, contextText, citation.title, openaiKey);
    }

    // Fallback: use the top chunk content directly
    if (!answer) {
      answer = topChunk.content.slice(0, 500);
    }

    const result: RagResult = {
      answer,
      citation,
      last_updated: citation?.last_updated ?? null,
      refused: false,
    };

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    const result: RagResult = {
      answer: 'An error occurred while processing your question. Please try again.',
      citation: null,
      last_updated: null,
      refused: false,
    };
    return new Response(JSON.stringify(result), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
