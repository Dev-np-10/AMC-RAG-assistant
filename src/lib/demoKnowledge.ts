import type { RagResponse, Citation } from '@/types';

interface KnowledgeEntry {
  keywords: string[];
  answer: string;
  citation: Citation;
}

export const AMC_NAME = 'HDFC Mutual Fund';

export const SCHEMES = [
  'HDFC Balanced Advantage Fund',
  'HDFC Mid-Cap Opportunities Fund',
  'HDFC Short Term Debt Fund',
  'HDFC Index Fund - Nifty 50 Plan',
] as const;

const BASE_URL = 'https://www.hdfcfund.com';

export const DEMO_SOURCES = [
  { source_id: 'hdfc-balanced-factsheet', amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', source_type: 'factsheet', url: `${BASE_URL}/factsheet/balanced-advantage`, title: 'HDFC Balanced Advantage Fund - Factsheet', last_updated: '2026-09-30' },
  { source_id: 'hdfc-balanced-sid', amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', source_type: 'scheme_information', url: `${BASE_URL}/sid/balanced-advantage`, title: 'HDFC Balanced Advantage Fund - Scheme Information Document', last_updated: '2026-09-30' },
  { source_id: 'hdfc-midcap-factsheet', amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', source_type: 'factsheet', url: `${BASE_URL}/factsheet/mid-cap-opportunities`, title: 'HDFC Mid-Cap Opportunities Fund - Factsheet', last_updated: '2026-09-30' },
  { source_id: 'hdfc-midcap-sid', amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', source_type: 'scheme_information', url: `${BASE_URL}/sid/mid-cap-opportunities`, title: 'HDFC Mid-Cap Opportunities Fund - Scheme Information Document', last_updated: '2026-09-30' },
  { source_id: 'hdfc-shortterm-factsheet', amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', source_type: 'factsheet', url: `${BASE_URL}/factsheet/short-term-debt`, title: 'HDFC Short Term Debt Fund - Factsheet', last_updated: '2026-09-30' },
  { source_id: 'hdfc-shortterm-sid', amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', source_type: 'scheme_information', url: `${BASE_URL}/sid/short-term-debt`, title: 'HDFC Short Term Debt Fund - Scheme Information Document', last_updated: '2026-09-30' },
  { source_id: 'hdfc-index-factsheet', amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', source_type: 'factsheet', url: `${BASE_URL}/factsheet/index-nifty-50`, title: 'HDFC Index Fund - Nifty 50 Plan - Factsheet', last_updated: '2026-09-30' },
  { source_id: 'hdfc-index-sid', amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', source_type: 'scheme_information', url: `${BASE_URL}/sid/index-nifty-50`, title: 'HDFC Index Fund - Nifty 50 Plan - Scheme Information Document', last_updated: '2026-09-30' },
  { source_id: 'sebi-circular-mutual-funds', amc: 'SEBI', scheme_name: '', source_type: 'sebi_circular', url: 'https://www.sebi.gov.in/circulars/mutual-funds', title: 'SEBI Circular on Mutual Fund Regulations', last_updated: '2026-09-30' },
  { source_id: 'amfi-scheme-codes', amc: 'AMFI', scheme_name: '', source_type: 'amfi_data', url: 'https://www.amfiindia.com/scheme-codes', title: 'AMFI Scheme Code Master List', last_updated: '2026-09-30' },
  { source_id: 'amfi-total-expense-ratio', amc: 'AMFI', scheme_name: '', source_type: 'amfi_data', url: 'https://www.amfiindia.com/ter', title: 'AMFI Total Expense Ratio Disclosure', last_updated: '2026-09-30' },
  { source_id: 'sebi-riskometer', amc: 'SEBI', scheme_name: '', source_type: 'sebi_circular', url: 'https://www.sebi.gov.in/circulars/riskometer', title: 'SEBI Riskometer Guidelines', last_updated: '2026-09-30' },
  { source_id: 'hdfc-balanced-kim', amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', source_type: 'scheme_information', url: `${BASE_URL}/kim/balanced-advantage`, title: 'HDFC Balanced Advantage Fund - Key Information Memorandum', last_updated: '2026-09-30' },
  { source_id: 'hdfc-midcap-kim', amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', source_type: 'scheme_information', url: `${BASE_URL}/kim/mid-cap-opportunities`, title: 'HDFC Mid-Cap Opportunities Fund - Key Information Memorandum', last_updated: '2026-09-30' },
  { source_id: 'hdfc-shortterm-kim', amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', source_type: 'scheme_information', url: `${BASE_URL}/kim/short-term-debt`, title: 'HDFC Short Term Debt Fund - Key Information Memorandum', last_updated: '2026-09-30' },
  { source_id: 'hdfc-index-kim', amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', source_type: 'scheme_information', url: `${BASE_URL}/kim/index-nifty-50`, title: 'HDFC Index Fund - Nifty 50 Plan - Key Information Memorandum', last_updated: '2026-09-30' },
  { source_id: 'hdfc-balanced-portfolio', amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', source_type: 'factsheet', url: `${BASE_URL}/portfolio/balanced-advantage`, title: 'HDFC Balanced Advantage Fund - Portfolio Statement', last_updated: '2026-09-30' },
  { source_id: 'hdfc-midcap-portfolio', amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', source_type: 'factsheet', url: `${BASE_URL}/portfolio/mid-cap-opportunities`, title: 'HDFC Mid-Cap Opportunities Fund - Portfolio Statement', last_updated: '2026-09-30' },
  { source_id: 'hdfc-shortterm-portfolio', amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', source_type: 'factsheet', url: `${BASE_URL}/portfolio/short-term-debt`, title: 'HDFC Short Term Debt Fund - Portfolio Statement', last_updated: '2026-09-30' },
  { source_id: 'hdfc-index-portfolio', amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', source_type: 'factsheet', url: `${BASE_URL}/portfolio/index-nifty-50`, title: 'HDFC Index Fund - Nifty 50 Plan - Portfolio Statement', last_updated: '2026-09-30' },
  { source_id: 'sebi-circular-ter', amc: 'SEBI', scheme_name: '', source_type: 'sebi_circular', url: 'https://www.sebi.gov.in/circulars/ter', title: 'SEBI Circular on Total Expense Ratio', last_updated: '2026-09-30' },
  { source_id: 'amfi-nav-history', amc: 'AMFI', scheme_name: '', source_type: 'amfi_data', url: 'https://www.amfiindia.com/nav-history', title: 'AMFI NAV History Database', last_updated: '2026-09-30' },
  { source_id: 'hdfc-balanced-addendum', amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', source_type: 'scheme_information', url: `${BASE_URL}/addendum/balanced-advantage`, title: 'HDFC Balanced Advantage Fund - Addendum', last_updated: '2026-09-30' },
  { source_id: 'hdfc-midcap-addendum', amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', source_type: 'scheme_information', url: `${BASE_URL}/addendum/mid-cap-opportunities`, title: 'HDFC Mid-Cap Opportunities Fund - Addendum', last_updated: '2026-09-30' },
];

const KNOWLEDGE: KnowledgeEntry[] = [
  {
    keywords: ['balanced advantage', 'expense ratio'],
    answer: 'The expense ratio of HDFC Balanced Advantage Fund is 1.50% for the Regular Plan and 0.85% for the Direct Plan, as per the latest factsheet. This includes the management fee and other recurring expenses charged to the scheme.',
    citation: { source_id: 'hdfc-balanced-factsheet', title: 'HDFC Balanced Advantage Fund - Factsheet', url: `${BASE_URL}/factsheet/balanced-advantage`, amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['balanced advantage', 'sip', 'minimum'],
    answer: 'The minimum SIP amount for HDFC Balanced Advantage Fund is Rs. 100 per installment. SIPs can be made on a monthly or quarterly basis with no upper limit.',
    citation: { source_id: 'hdfc-balanced-sid', title: 'HDFC Balanced Advantage Fund - Scheme Information Document', url: `${BASE_URL}/sid/balanced-advantage`, amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['balanced advantage', 'exit load'],
    answer: 'HDFC Balanced Advantage Fund charges an exit load of 1% if units are redeemed within 90 days of allotment. No exit load is applicable for redemptions after 90 days.',
    citation: { source_id: 'hdfc-balanced-sid', title: 'HDFC Balanced Advantage Fund - Scheme Information Document', url: `${BASE_URL}/sid/balanced-advantage`, amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['balanced advantage', 'riskometer', 'risk'],
    answer: 'HDFC Balanced Advantage Fund is rated as "Moderately High Risk" on the SEBI Riskometer. This reflects the dynamic asset allocation between equity and debt instruments.',
    citation: { source_id: 'hdfc-balanced-kim', title: 'HDFC Balanced Advantage Fund - Key Information Memorandum', url: `${BASE_URL}/kim/balanced-advantage`, amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['balanced advantage', 'benchmark'],
    answer: 'The benchmark for HDFC Balanced Advantage Fund is Nifty 50 Hybrid Composite Debt 50:50 Index. The scheme aims to generate returns through dynamic asset allocation between equity and debt.',
    citation: { source_id: 'hdfc-balanced-factsheet', title: 'HDFC Balanced Advantage Fund - Factsheet', url: `${BASE_URL}/factsheet/balanced-advantage`, amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['balanced advantage', 'lock-in'],
    answer: 'HDFC Balanced Advantage Fund has no lock-in period. It is an open-ended dynamic asset allocation fund and units can be redeemed on any business day, subject to applicable exit load.',
    citation: { source_id: 'hdfc-balanced-sid', title: 'HDFC Balanced Advantage Fund - Scheme Information Document', url: `${BASE_URL}/sid/balanced-advantage`, amc: AMC_NAME, scheme_name: 'HDFC Balanced Advantage Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['mid-cap', 'midcap', 'expense ratio'],
    answer: 'The expense ratio of HDFC Mid-Cap Opportunities Fund is 1.75% for the Regular Plan and 1.05% for the Direct Plan, as per the latest factsheet.',
    citation: { source_id: 'hdfc-midcap-factsheet', title: 'HDFC Mid-Cap Opportunities Fund - Factsheet', url: `${BASE_URL}/factsheet/mid-cap-opportunities`, amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['mid-cap', 'midcap', 'sip', 'minimum'],
    answer: 'The minimum SIP amount for HDFC Mid-Cap Opportunities Fund is Rs. 100 per installment. SIPs are available on a monthly or quarterly frequency.',
    citation: { source_id: 'hdfc-midcap-sid', title: 'HDFC Mid-Cap Opportunities Fund - Scheme Information Document', url: `${BASE_URL}/sid/mid-cap-opportunities`, amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['mid-cap', 'midcap', 'exit load'],
    answer: 'HDFC Mid-Cap Opportunities Fund charges an exit load of 1% if units are redeemed within 365 days of allotment. No exit load applies after 365 days.',
    citation: { source_id: 'hdfc-midcap-sid', title: 'HDFC Mid-Cap Opportunities Fund - Scheme Information Document', url: `${BASE_URL}/sid/mid-cap-opportunities`, amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['mid-cap', 'midcap', 'riskometer', 'risk'],
    answer: 'HDFC Mid-Cap Opportunities Fund is rated as "High Risk" on the SEBI Riskometer. Mid-cap investments carry higher volatility and risk compared to large-cap funds.',
    citation: { source_id: 'hdfc-midcap-kim', title: 'HDFC Mid-Cap Opportunities Fund - Key Information Memorandum', url: `${BASE_URL}/kim/mid-cap-opportunities`, amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['mid-cap', 'midcap', 'benchmark'],
    answer: 'The benchmark for HDFC Mid-Cap Opportunities Fund is Nifty Midcap 150 TRI. The fund invests predominantly in mid-cap stocks to generate long-term capital appreciation.',
    citation: { source_id: 'hdfc-midcap-factsheet', title: 'HDFC Mid-Cap Opportunities Fund - Factsheet', url: `${BASE_URL}/factsheet/mid-cap-opportunities`, amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['mid-cap', 'midcap', 'lock-in'],
    answer: 'HDFC Mid-Cap Opportunities Fund has no lock-in period. It is an open-ended equity scheme and units can be redeemed on any business day, subject to applicable exit load.',
    citation: { source_id: 'hdfc-midcap-sid', title: 'HDFC Mid-Cap Opportunities Fund - Scheme Information Document', url: `${BASE_URL}/sid/mid-cap-opportunities`, amc: AMC_NAME, scheme_name: 'HDFC Mid-Cap Opportunities Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['short term debt', 'short-term', 'expense ratio'],
    answer: 'The expense ratio of HDFC Short Term Debt Fund is 0.85% for the Regular Plan and 0.45% for the Direct Plan, as per the latest factsheet.',
    citation: { source_id: 'hdfc-shortterm-factsheet', title: 'HDFC Short Term Debt Fund - Factsheet', url: `${BASE_URL}/factsheet/short-term-debt`, amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['short term debt', 'short-term', 'sip', 'minimum'],
    answer: 'The minimum SIP amount for HDFC Short Term Debt Fund is Rs. 1,000 per installment. SIPs are available on a monthly or quarterly basis.',
    citation: { source_id: 'hdfc-shortterm-sid', title: 'HDFC Short Term Debt Fund - Scheme Information Document', url: `${BASE_URL}/sid/short-term-debt`, amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['short term debt', 'short-term', 'exit load'],
    answer: 'HDFC Short Term Debt Fund charges an exit load of 0.50% if units are redeemed within 3 months of allotment. No exit load applies after 3 months.',
    citation: { source_id: 'hdfc-shortterm-sid', title: 'HDFC Short Term Debt Fund - Scheme Information Document', url: `${BASE_URL}/sid/short-term-debt`, amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['short term debt', 'short-term', 'riskometer', 'risk'],
    answer: 'HDFC Short Term Debt Fund is rated as "Low to Moderate Risk" on the SEBI Riskometer. It invests in short-term debt instruments with relatively lower interest rate risk.',
    citation: { source_id: 'hdfc-shortterm-kim', title: 'HDFC Short Term Debt Fund - Key Information Memorandum', url: `${BASE_URL}/kim/short-term-debt`, amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['short term debt', 'short-term', 'benchmark'],
    answer: 'The benchmark for HDFC Short Term Debt Fund is NIFTY Short Duration Debt Index. The fund aims to generate income through investments in short-duration debt securities.',
    citation: { source_id: 'hdfc-shortterm-factsheet', title: 'HDFC Short Term Debt Fund - Factsheet', url: `${BASE_URL}/factsheet/short-term-debt`, amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['short term debt', 'short-term', 'lock-in'],
    answer: 'HDFC Short Term Debt Fund has no lock-in period. It is an open-ended debt scheme and units can be redeemed on any business day, subject to applicable exit load.',
    citation: { source_id: 'hdfc-shortterm-sid', title: 'HDFC Short Term Debt Fund - Scheme Information Document', url: `${BASE_URL}/sid/short-term-debt`, amc: AMC_NAME, scheme_name: 'HDFC Short Term Debt Fund', last_updated: '2026-09-30' },
  },
  {
    keywords: ['index fund', 'nifty 50', 'expense ratio'],
    answer: 'The expense ratio of HDFC Index Fund - Nifty 50 Plan is 0.40% for the Regular Plan and 0.20% for the Direct Plan, as per the latest factsheet. Being a passive fund, it has lower expenses than actively managed funds.',
    citation: { source_id: 'hdfc-index-factsheet', title: 'HDFC Index Fund - Nifty 50 Plan - Factsheet', url: `${BASE_URL}/factsheet/index-nifty-50`, amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', last_updated: '2026-09-30' },
  },
  {
    keywords: ['index fund', 'nifty 50', 'sip', 'minimum'],
    answer: 'The minimum SIP amount for HDFC Index Fund - Nifty 50 Plan is Rs. 100 per installment. SIPs are available on a monthly or quarterly basis.',
    citation: { source_id: 'hdfc-index-sid', title: 'HDFC Index Fund - Nifty 50 Plan - Scheme Information Document', url: `${BASE_URL}/sid/index-nifty-50`, amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', last_updated: '2026-09-30' },
  },
  {
    keywords: ['index fund', 'nifty 50', 'exit load'],
    answer: 'HDFC Index Fund - Nifty 50 Plan charges an exit load of 0.50% if units are redeemed within 30 days of allotment. No exit load applies after 30 days.',
    citation: { source_id: 'hdfc-index-sid', title: 'HDFC Index Fund - Nifty 50 Plan - Scheme Information Document', url: `${BASE_URL}/sid/index-nifty-50`, amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', last_updated: '2026-09-30' },
  },
  {
    keywords: ['index fund', 'nifty 50', 'riskometer', 'risk'],
    answer: 'HDFC Index Fund - Nifty 50 Plan is rated as "Very High Risk" on the SEBI Riskometer. As a pure equity index fund, it carries the full market risk of the Nifty 50 index.',
    citation: { source_id: 'hdfc-index-kim', title: 'HDFC Index Fund - Nifty 50 Plan - Key Information Memorandum', url: `${BASE_URL}/kim/index-nifty-50`, amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', last_updated: '2026-09-30' },
  },
  {
    keywords: ['index fund', 'nifty 50', 'benchmark'],
    answer: 'The benchmark for HDFC Index Fund - Nifty 50 Plan is NIFTY 50 TRI. The fund passively replicates the Nifty 50 index by investing in the same stocks in the same proportion.',
    citation: { source_id: 'hdfc-index-factsheet', title: 'HDFC Index Fund - Nifty 50 Plan - Factsheet', url: `${BASE_URL}/factsheet/index-nifty-50`, amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', last_updated: '2026-09-30' },
  },
  {
    keywords: ['index fund', 'nifty 50', 'lock-in'],
    answer: 'HDFC Index Fund - Nifty 50 Plan has no lock-in period. It is an open-ended index scheme and units can be redeemed on any business day, subject to applicable exit load.',
    citation: { source_id: 'hdfc-index-sid', title: 'HDFC Index Fund - Nifty 50 Plan - Scheme Information Document', url: `${BASE_URL}/sid/index-nifty-50`, amc: AMC_NAME, scheme_name: 'HDFC Index Fund - Nifty 50 Plan', last_updated: '2026-09-30' },
  },
];

function scoreEntry(question: string, entry: KnowledgeEntry): number {
  const q = question.toLowerCase();
  let score = 0;
  for (const kw of entry.keywords) {
    if (q.includes(kw.toLowerCase())) score += kw.length;
  }
  return score;
}

export function demoSearch(question: string): RagResponse {
  let best: KnowledgeEntry | null = null;
  let bestScore = 0;

  for (const entry of KNOWLEDGE) {
    const score = scoreEntry(question, entry);
    if (score > bestScore) {
      bestScore = score;
      best = entry;
    }
  }

  if (!best || bestScore === 0) {
    return {
      answer: 'I could not find any factual information about this in the ingested sources. Please try asking about expense ratio, SIP, exit load, lock-in period, riskometer, or benchmark for any of the four HDFC schemes covered.',
      citation: null,
      last_updated: '2026-09-30',
      refused: false,
    };
  }

  return {
    answer: best.answer,
    citation: best.citation,
    last_updated: best.citation.last_updated,
    refused: false,
  };
}

export const EXAMPLE_QUESTIONS = [
  'What is the expense ratio of HDFC Balanced Advantage Fund?',
  'What is the exit load for HDFC Mid-Cap Opportunities Fund?',
  'What is the riskometer rating of HDFC Short Term Debt Fund?',
];
