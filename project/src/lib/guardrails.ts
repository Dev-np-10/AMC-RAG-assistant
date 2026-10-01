const PII_PATTERNS = [
  /\b[A-Z]{5}\d{4}[A-Z]\b/,
  /\b\d{12}\b/,
  /\b\d{4}\s?\d{4}\s?\d{4}\b/,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
  /\b\d{10}\b/,
  /\b\d{6}\b/,
  /\b(?:\+\d{1,3}[-\s]?)?\d{10}\b/,
  /\b(?:PAN|Aadhaar|OTP|account\s*(?:number|no)?)\b/i,
];

const ADVICE_PATTERNS = [
  /should\s+i\s*(?:invest|buy|sell|redeem|switch)/i,
  /which\s*(?:fund|scheme)\s*(?:should|to)\s*(?:i\s*)?(?:invest|buy|choose)/i,
  /is\s*(?:it|this)\s*(?:a\s*)?(?:good|bad)\s*(?:time|investment)/i,
  /recommend\s/i,
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

export interface GuardrailResult {
  blocked: boolean;
  reason: string;
}

export function checkGuardrails(question: string): GuardrailResult {
  for (const pattern of PII_PATTERNS) {
    if (pattern.test(question)) {
      return {
        blocked: true,
        reason: 'Your question appears to contain sensitive personal information (PAN, Aadhaar, OTP, phone, email, or account details). For your security, I cannot process questions containing PII. Please rephrase your question without personal details.',
      };
    }
  }

  for (const pattern of ADVICE_PATTERNS) {
    if (pattern.test(question)) {
      return {
        blocked: true,
        reason: 'I am a facts-only chatbot and cannot provide investment advice, recommendations, return predictions, or comparisons. I can only answer factual questions about expense ratio, SIP, exit load, lock-in period, riskometer, benchmark, and scheme statements from official sources. Please ask a factual question instead.',
      };
    }
  }

  return { blocked: false, reason: '' };
}
