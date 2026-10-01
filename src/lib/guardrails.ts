export interface GuardrailResult {
  blocked: boolean;
  reason: string;
  category?: 'PII' | 'ADVICE' | 'PERFORMANCE' | 'OUT_OF_SCOPE' | 'FACTUAL';
}

const PII_PATTERNS = [
  /[A-Z]{5}\d{4}[A-Z]/,
  /\b\d{12}\b/,
  /\b\d{4}\s?\d{4}\s?\d{4}\b/,
  /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
  /\b\d{10}\b/,
  /\b\d{6}\b/,
  /\b(?:\+\d{1,3}[-\s]?)?\d{10}\b/,
  /\b(?:PAN|Aadhaar|OTP|account\s*(?:number|no)?)\b/i,
];

const ADVICE_PATTERNS = [
  /should\s+i\s*(?:invest|buy|sell|redeem|switch)/i,
  /which\s*(?:fund|scheme)\s*(?:should|to)\s*(?:i\s*)?(?:invest|buy|choose)/i,
  /is\s*(?:it|this)\s*(?:a\s*)?(?:good|bad)\s*(?:time|investment)/i,
  /is\s+.*(?:good|bad|safe)\s*(?:investment|to invest)?/i,
  /is\s+(?:hdfc|this).*(?:fund|scheme).*(?:safe|good|bad)/i,
  /recommend/i,
  /best\s*(?:fund|scheme|investment)/i,
  /should\s+i\s*(?:hold|exit|continue)/i,
  /portfolio\s*(?:allocation|recommendation|suggestion)/i,
  /how\s*(?:much|should)\s*i\s*invest/i,
];

const PERFORMANCE_PATTERNS = [
  /will\s+.*(?:nav|return|fund).*(?:increase|decrease|rise|fall|go|grow)/i,
  /will\s*(?:the\s*)?(?:nav|return|fund)\s*(?:go|be|increase|decrease)/i,
  /predict/i,
  /future\s*(?:return|performance|nav)/i,
  /compare\s*(?:the\s*)?(?:return|performance|nav)/i,
  /which\s*is\s*better/i,
  /(?:past|historical|expected)\s*(?:return|performance|yield)/i,
  /(?:cagr|annualized?\s*return|total\s*return)/i,
];

export function checkGuardrails(question: string): GuardrailResult {
  const q = question.trim();
  if (!q) {
    return { blocked: true, reason: 'Please enter a valid question.', category: 'OUT_OF_SCOPE' };
  }

  for (const pattern of PII_PATTERNS) {
    if (pattern.test(q)) {
      return {
        blocked: true,
        reason:
          'Your question appears to contain sensitive personal information (PAN, Aadhaar, OTP, phone, email, or account details). For your security, I cannot process questions containing PII. Please rephrase your question without personal details.',
        category: 'PII',
      };
    }
  }

  for (const pattern of ADVICE_PATTERNS) {
    if (pattern.test(q)) {
      return {
        blocked: true,
        reason:
          'I am a facts-only chatbot and cannot provide investment advice, recommendations, or suggestions. I can only answer factual questions about expense ratio, SIP, exit load, lock-in period, riskometer, benchmark, and scheme statements from official sources. Please ask a factual question instead.',
        category: 'ADVICE',
      };
    }
  }

  for (const pattern of PERFORMANCE_PATTERNS) {
    if (pattern.test(q)) {
      return {
        blocked: true,
        reason:
          'I cannot provide return predictions, performance forecasts, or fund comparisons. I can only state factual attributes from official source documents. Please ask about expense ratio, SIP, exit load, lock-in, riskometer, or benchmark instead.',
        category: 'PERFORMANCE',
      };
    }
  }

  return { blocked: false, reason: '', category: 'FACTUAL' };
}
