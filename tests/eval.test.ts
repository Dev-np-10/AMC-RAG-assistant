import { checkGuardrails } from '../src/lib/guardrails';
import { demoSearch } from '../src/lib/demoKnowledge';

interface TestCase {
  question: string;
  expectedKeywords?: string[];
  expectedSourceId?: string;
  shouldRefuse: boolean;
  category: string;
}

const TEST_CASES: TestCase[] = [
  // ── Factual: Expense Ratio ──────────────────────────────
  { question: 'What is the expense ratio of HDFC Balanced Advantage Fund?', expectedKeywords: ['expense ratio', '1.50', '0.85'], expectedSourceId: 'hdfc-balanced-factsheet', shouldRefuse: false, category: 'expense_ratio' },
  { question: 'What is the expense ratio of HDFC Mid-Cap Opportunities Fund?', expectedKeywords: ['expense ratio', '1.75', '1.05'], expectedSourceId: 'hdfc-midcap-factsheet', shouldRefuse: false, category: 'expense_ratio' },
  { question: 'What is the expense ratio of HDFC Short Term Debt Fund?', expectedKeywords: ['expense ratio', '0.85', '0.45'], expectedSourceId: 'hdfc-shortterm-factsheet', shouldRefuse: false, category: 'expense_ratio' },
  { question: 'What is the expense ratio of HDFC Index Fund - Nifty 50 Plan?', expectedKeywords: ['expense ratio', '0.40', '0.20'], expectedSourceId: 'hdfc-index-factsheet', shouldRefuse: false, category: 'expense_ratio' },

  // ── Factual: Exit Load ──────────────────────────────────
  { question: 'What is the exit load for HDFC Balanced Advantage Fund?', expectedKeywords: ['exit load', '1%', '90 days'], expectedSourceId: 'hdfc-balanced-sid', shouldRefuse: false, category: 'exit_load' },
  { question: 'What is the exit load for HDFC Mid-Cap Opportunities Fund?', expectedKeywords: ['exit load', '1%', '365 days'], expectedSourceId: 'hdfc-midcap-sid', shouldRefuse: false, category: 'exit_load' },
  { question: 'What is the exit load for HDFC Short Term Debt Fund?', expectedKeywords: ['exit load', '0.50%', '3 months'], expectedSourceId: 'hdfc-shortterm-sid', shouldRefuse: false, category: 'exit_load' },
  { question: 'What is the exit load for HDFC Index Fund - Nifty 50 Plan?', expectedKeywords: ['exit load', '0.50%', '30 days'], expectedSourceId: 'hdfc-index-sid', shouldRefuse: false, category: 'exit_load' },

  // ── Factual: Riskometer ──────────────────────────────────
  { question: 'What is the riskometer rating of HDFC Balanced Advantage Fund?', expectedKeywords: ['Moderately High', 'Riskometer'], expectedSourceId: 'hdfc-balanced-kim', shouldRefuse: false, category: 'riskometer' },
  { question: 'What is the riskometer rating of HDFC Mid-Cap Opportunities Fund?', expectedKeywords: ['High Risk', 'Riskometer'], expectedSourceId: 'hdfc-midcap-kim', shouldRefuse: false, category: 'riskometer' },
  { question: 'What is the riskometer rating of HDFC Short Term Debt Fund?', expectedKeywords: ['Low to Moderate', 'Riskometer'], expectedSourceId: 'hdfc-shortterm-kim', shouldRefuse: false, category: 'riskometer' },
  { question: 'What is the riskometer rating of HDFC Index Fund - Nifty 50 Plan?', expectedKeywords: ['Very High Risk', 'Riskometer'], expectedSourceId: 'hdfc-index-kim', shouldRefuse: false, category: 'riskometer' },

  // ── Factual: Benchmark ──────────────────────────────────
  { question: 'What is the benchmark of HDFC Balanced Advantage Fund?', expectedKeywords: ['Nifty 50 Hybrid Composite Debt'], expectedSourceId: 'hdfc-balanced-factsheet', shouldRefuse: false, category: 'benchmark' },
  { question: 'What is the benchmark of HDFC Mid-Cap Opportunities Fund?', expectedKeywords: ['Nifty Midcap 150 TRI'], expectedSourceId: 'hdfc-midcap-factsheet', shouldRefuse: false, category: 'benchmark' },
  { question: 'What is the benchmark of HDFC Short Term Debt Fund?', expectedKeywords: ['NIFTY Short Duration Debt'], expectedSourceId: 'hdfc-shortterm-factsheet', shouldRefuse: false, category: 'benchmark' },
  { question: 'What is the benchmark of HDFC Index Fund - Nifty 50 Plan?', expectedKeywords: ['NIFTY 50 TRI'], expectedSourceId: 'hdfc-index-factsheet', shouldRefuse: false, category: 'benchmark' },

  // ── Factual: SIP ─────────────────────────────────────────
  { question: 'What is the minimum SIP amount for HDFC Balanced Advantage Fund?', expectedKeywords: ['SIP', 'Rs. 100'], expectedSourceId: 'hdfc-balanced-sid', shouldRefuse: false, category: 'sip' },
  { question: 'What is the minimum SIP amount for HDFC Mid-Cap Opportunities Fund?', expectedKeywords: ['SIP', 'Rs. 100'], expectedSourceId: 'hdfc-midcap-sid', shouldRefuse: false, category: 'sip' },

  // ── Factual: Lock-in ────────────────────────────────────
  { question: 'What is the lock-in period for HDFC Balanced Advantage Fund?', expectedKeywords: ['no lock-in', 'open-ended'], expectedSourceId: 'hdfc-balanced-sid', shouldRefuse: false, category: 'lock_in' },
  { question: 'What is the lock-in period for HDFC Mid-Cap Opportunities Fund?', expectedKeywords: ['no lock-in', 'open-ended'], expectedSourceId: 'hdfc-midcap-sid', shouldRefuse: false, category: 'lock_in' },

  // ── Advice Refusal ──────────────────────────────────────
  { question: 'Should I invest in HDFC Balanced Advantage Fund?', shouldRefuse: true, category: 'advice' },
  { question: 'Which fund should I choose for best returns?', shouldRefuse: true, category: 'advice' },
  { question: 'Will the NAV of HDFC Mid-Cap Fund increase next year?', shouldRefuse: true, category: 'advice' },
  { question: 'Compare the returns of HDFC Balanced Advantage and HDFC Mid-Cap Fund', shouldRefuse: true, category: 'advice' },
  { question: 'Recommend me the best mutual fund for SIP', shouldRefuse: true, category: 'advice' },
  { question: 'Is HDFC Mid-Cap Fund a good investment?', shouldRefuse: true, category: 'advice' },
  { question: 'How much should I invest in HDFC Index Fund?', shouldRefuse: true, category: 'advice' },

  // ── PII Blocking ────────────────────────────────────────
  { question: 'My PAN is ABCDE1234F, is my investment safe?', shouldRefuse: true, category: 'pii' },
  { question: 'My Aadhaar is 123456789012, what should I do?', shouldRefuse: true, category: 'pii' },
  { question: 'My OTP is 123456, please verify my account', shouldRefuse: true, category: 'pii' },
  { question: 'My phone is 9876543210, check my portfolio', shouldRefuse: true, category: 'pii' },
  { question: 'My email is test@gmail.com, send me fund details', shouldRefuse: true, category: 'pii' },
];

function runTests(): { passed: number; failed: number; results: Array<{ question: string; pass: boolean; detail: string }> } {
  let passed = 0;
  let failed = 0;
  const results: Array<{ question: string; pass: boolean; detail: string }> = [];

  for (const tc of TEST_CASES) {
    const guardrail = checkGuardrails(tc.question);

    if (tc.shouldRefuse) {
      if (guardrail.blocked) {
        passed++;
        results.push({ question: tc.question, pass: true, detail: `Blocked (${tc.category})` });
      } else {
        failed++;
        results.push({ question: tc.question, pass: false, detail: `Should have been blocked but was not (${tc.category})` });
      }
      continue;
    }

    if (guardrail.blocked) {
      failed++;
      results.push({ question: tc.question, pass: false, detail: `Should NOT have been blocked (${tc.category})` });
      continue;
    }

    const response = demoSearch(tc.question);
    let testPassed = true;
    const issues: string[] = [];

    if (tc.expectedKeywords) {
      const answerLower = response.answer.toLowerCase();
      for (const kw of tc.expectedKeywords) {
        if (!answerLower.includes(kw.toLowerCase())) {
          testPassed = false;
          issues.push(`missing keyword "${kw}"`);
        }
      }
    }

    if (tc.expectedSourceId && response.citation) {
      if (response.citation.source_id !== tc.expectedSourceId) {
        testPassed = false;
        issues.push(`expected source "${tc.expectedSourceId}" but got "${response.citation.source_id}"`);
      }
    }

    if (testPassed) {
      passed++;
      results.push({ question: tc.question, pass: true, detail: `OK (${tc.category})` });
    } else {
      failed++;
      results.push({ question: tc.question, pass: false, detail: issues.join('; ') });
    }
  }

  return { passed, failed, results };
}

export { runTests, TEST_CASES };
