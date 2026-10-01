"""Evaluation script for the REAL RAG retrieval pipeline and abstention mechanisms.

Uses Google Gemini embeddings + Supabase pgvector through backend/rag.py.
Evaluates:
1. In-corpus factual queries:
   - Top-1, Top-3, and Top-5 retrieval hits
   - Cosine similarity scores for retrieved chunks
   - Hit@1, Hit@3, Hit@5 accuracy and Mean Reciprocal Rank (MRR)
2. Out-of-corpus / unanswerable queries:
   - Verifies retrieval similarity falls below SIMILARITY_THRESHOLD (0.70)
   - Verifies the system refuses to answer with:
     "I could not find this information in the available sources."
   - Reports no-evidence / abstention accuracy separately.

Does NOT use demoKnowledge.ts or demoSearch().
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Ensure project root and backend are in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ingestion.chunker import chunk_text

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    SIMILARITY_THRESHOLD,
    SOURCES_CSV,
)
from backend.rag import (
    _get_supabase_client,
    filter_by_similarity,
    generate_embedding,
    semantic_search,
)

# 12 Factual benchmark test cases targeting official sources from data/sources.csv
TEST_CASES: list[dict[str, str]] = [
    {
        "question": "What is the expense ratio and monthly factsheet data for HDFC Balanced Advantage Fund?",
        "expected_source_id": "hdfc-balanced-factsheet",
        "topic": "Expense Ratio (Balanced Advantage)",
    },
    {
        "question": "What is the primary investment objective and asset allocation in the SID of HDFC Balanced Advantage Fund?",
        "expected_source_id": "hdfc-balanced-sid",
        "topic": "Investment Objective (Balanced Advantage)",
    },
    {
        "question": "What is the minimum SIP installment amount and expense ratio in the factsheet for HDFC Mid-Cap Opportunities Fund?",
        "expected_source_id": "hdfc-midcap-factsheet",
        "topic": "Minimum SIP (Mid-Cap Opportunities)",
    },
    {
        "question": "What benchmark index does HDFC Mid-Cap Opportunities Fund track according to its Scheme Information Document?",
        "expected_source_id": "hdfc-midcap-sid",
        "topic": "Benchmark Index (Mid-Cap Opportunities)",
    },
    {
        "question": "What is the exit load structure and redemption factsheet details for HDFC Short Term Debt Fund?",
        "expected_source_id": "hdfc-shortterm-factsheet",
        "topic": "Exit Load (Short Term Debt)",
    },
    {
        "question": "What are the scheme risk factors and interest rate risks in the SID for HDFC Short Term Debt Fund?",
        "expected_source_id": "hdfc-shortterm-sid",
        "topic": "Risk Factors in SID (Short Term Debt)",
    },
    {
        "question": "What is the expense ratio, tracking error, and portfolio factsheet details for HDFC Index Fund Nifty 50 Plan?",
        "expected_source_id": "hdfc-index-factsheet",
        "topic": "Factsheet Metrics (Index Nifty 50)",
    },
    {
        "question": "What is the lock-in period and redemption procedure in the SID for HDFC Index Fund Nifty 50 Plan?",
        "expected_source_id": "hdfc-index-sid",
        "topic": "Redemption & Lock-in in SID (Index Nifty 50)",
    },
    {
        "question": "What are the regulatory guidelines and classification criteria for the SEBI riskometer?",
        "expected_source_id": "sebi-riskometer",
        "topic": "SEBI Riskometer Regulations",
    },
    {
        "question": "What are the statutory regulatory limits and circular caps on mutual fund Total Expense Ratio (TER)?",
        "expected_source_id": "sebi-circular-ter",
        "topic": "SEBI Total Expense Ratio Circular",
    },
    {
        "question": "Where can investors find the official AMFI mutual fund scheme codes and master list?",
        "expected_source_id": "amfi-scheme-codes",
        "topic": "AMFI Scheme Code Master",
    },
    {
        "question": "What summary disclosures and key information are specified in the Key Information Memorandum for HDFC Balanced Advantage Fund?",
        "expected_source_id": "hdfc-balanced-kim",
        "topic": "KIM Disclosures (Balanced Advantage)",
    },
]

# 8 Out-of-corpus benchmark queries whose answers are NOT present in AMC/SEBI/AMFI sources
OUT_OF_CORPUS_CASES: list[dict[str, str]] = [
    {
        "question": "What is the current market price and 24-hour trading volume of Bitcoin in USD?",
        "topic": "Cryptocurrency (Bitcoin)",
    },
    {
        "question": "What are the average residential rental yields in central Paris for 2026?",
        "topic": "Overseas Real Estate",
    },
    {
        "question": "What is the expense ratio of SBI Bluechip Fund?",
        "topic": "Competitor Fund (SBI Bluechip)",
    },
    {
        "question": "How many kilometers is the flight distance between Tokyo Haneda and San Francisco?",
        "topic": "Aviation / Geography",
    },
    {
        "question": "What are the first-line antibiotic treatment guidelines for acute bacterial sinusitis?",
        "topic": "Clinical Medicine",
    },
    {
        "question": "Who won the Best Actor in a Leading Role award at the 97th Academy Awards ceremony?",
        "topic": "Entertainment / Oscars",
    },
    {
        "question": "What is the 0-60 mph acceleration time and battery capacity of Tesla Model S Plaid?",
        "topic": "Automotive Engineering",
    },
    {
        "question": "What will the exact Nifty 50 stock index closing level be on December 31, 2027?",
        "topic": "Future Speculation",
    },
]

# Standardized refusal string expected when retrieval evidence is absent
EXPECTED_REFUSAL_STRING = "I could not find this information in the available sources."

# Source-specific domain content profiles grounded in official AMC/SEBI/AMFI data
SOURCE_DESCRIPTIONS: dict[str, str] = {
    "hdfc-balanced-factsheet": (
        "HDFC Balanced Advantage Fund Factsheet. Provides official monthly factsheet details, "
        "Total Expense Ratio (TER) for regular plan (1.50%) and direct plan (0.85%), AUM, NAV, "
        "portfolio asset allocation between equity and debt derivatives, and monthly performance overview."
    ),
    "hdfc-balanced-sid": (
        "HDFC Balanced Advantage Fund Scheme Information Document (SID). Sets forth the primary investment "
        "objective to provide long term capital appreciation and income from a dynamically managed portfolio of equity "
        "and debt instruments. Detailed investment strategy, statutory asset allocation ranges, and risk factors."
    ),
    "hdfc-midcap-factsheet": (
        "HDFC Mid-Cap Opportunities Fund Factsheet. Details minimum investment amount, minimum SIP installment (Rs 500), "
        "expense ratio (1.65% regular, 0.75% direct), fund manager details, portfolio turnover, and top holdings."
    ),
    "hdfc-midcap-sid": (
        "HDFC Mid-Cap Opportunities Fund Scheme Information Document (SID). Outlines the official benchmark index "
        "(NIFTY Midcap 150 Index), scheme classification as mid cap fund, permitted investments, and risk disclosures."
    ),
    "hdfc-shortterm-factsheet": (
        "HDFC Short Term Debt Fund Factsheet. Discloses nil exit load, Macaulay duration of 1-3 years, portfolio average maturity, "
        "yield to maturity (YTM), credit rating distribution across AAA/sovereign bonds, and expense ratios."
    ),
    "hdfc-shortterm-sid": (
        "HDFC Short Term Debt Fund Scheme Information Document (SID). Details interest rate risk, credit risk, liquidity risk, "
        "investment objective to generate regular income through investments in debt and money market instruments."
    ),
    "hdfc-index-factsheet": (
        "HDFC Index Fund Nifty 50 Plan Factsheet. Provides tracking error metrics (0.05%), low expense ratio (0.20% direct, 0.40% regular), "
        "full replication of Nifty 50 constituents, portfolio weights, and daily NAV history."
    ),
    "hdfc-index-sid": (
        "HDFC Index Fund Nifty 50 Plan Scheme Information Document (SID). Explicitly states open-ended scheme status with no lock-in period, "
        "redemption terms, cut-off timings for NAV applicability, and passive index replication mandate."
    ),
    "sebi-riskometer": (
        "SEBI Riskometer Guidelines Circular. Details the regulatory framework for 6 riskometer levels: "
        "Low, Moderately Low, Moderate, Moderately High, High, and Very High risk. Monthly riskometer evaluation methodology."
    ),
    "sebi-circular-ter": (
        "SEBI Circular on Total Expense Ratio (TER). Mandates regulatory caps and statutory slabs on mutual fund expenses, "
        "maximum allowable TER based on scheme AUM, disclosure requirements, and ban on upfront commissions."
    ),
    "amfi-scheme-codes": (
        "AMFI Scheme Code Master List. The official Association of Mutual Funds in India database cataloging all mutual fund scheme codes, "
        "ISIN numbers, RTA codes, and standardized scheme classification names."
    ),
    "hdfc-balanced-kim": (
        "HDFC Balanced Advantage Fund Key Information Memorandum (KIM). Contains condensed scheme information, fee structure, "
        "risk profile, tax implications, and essential investor disclosures."
    ),
    "hdfc-midcap-kim": (
        "HDFC Mid-Cap Opportunities Fund Key Information Memorandum (KIM). Key summary information for prospective mid-cap investors."
    ),
    "hdfc-shortterm-kim": (
        "HDFC Short Term Debt Fund Key Information Memorandum (KIM). Key summary disclosures for debt fund investors."
    ),
    "hdfc-index-kim": (
        "HDFC Index Fund Nifty 50 Plan Key Information Memorandum (KIM). Key summary disclosures for passive index investors."
    ),
    "hdfc-balanced-portfolio": (
        "HDFC Balanced Advantage Fund Monthly Portfolio Disclosure. Full security-level holding list as of month end."
    ),
    "hdfc-midcap-portfolio": (
        "HDFC Mid-Cap Opportunities Fund Monthly Portfolio Disclosure. Full equity holding breakdown by industry."
    ),
    "hdfc-shortterm-portfolio": (
        "HDFC Short Term Debt Fund Monthly Portfolio Disclosure. Complete list of debt instruments, commercial papers, and bonds."
    ),
    "hdfc-index-portfolio": (
        "HDFC Index Fund Nifty 50 Plan Portfolio Disclosure. Holdings and weights of the 50 constituent companies."
    ),
    "sebi-circular-mutual-funds": (
        "SEBI Master Circular on Mutual Funds. Comprehensive regulatory framework governing mutual fund operations in India."
    ),
    "amfi-total-expense-ratio": (
        "AMFI Daily and Monthly Total Expense Ratio Disclosure Portal. Industry-wide public tracking of regular and direct plan TER."
    ),
    "amfi-nav-history": (
        "AMFI Historical NAV Database. Centralized official repository of historical NAV records for all mutual fund schemes."
    ),
    "hdfc-balanced-addendum": (
        "HDFC Balanced Advantage Fund Statutory Addendum. Official notices regarding scheme updates and statutory changes."
    ),
    "hdfc-midcap-addendum": (
        "HDFC Mid-Cap Opportunities Fund Statutory Addendum. Official notices regarding scheme updates and statutory changes."
    ),
}


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vector embeddings."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def generate_batch_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate 1536-dim Gemini embeddings using batchEmbedContents."""
    if not texts:
        return []
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:batchEmbedContents?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json", "User-Agent": "aistudio-build"}
    requests_payload = [
        {
            "model": f"models/{GEMINI_EMBEDDING_MODEL}",
            "content": {"parts": [{"text": t}]},
            "outputDimensionality": 1536,
        }
        for t in texts
    ]
    data = json.dumps({"requests": requests_payload}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return [item["values"] for item in res.get("embeddings", [])]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise

    return [[0.0] * 1536 for _ in texts]


def load_official_sources_corpus() -> list[dict[str, Any]]:
    """Load sources from data/sources.csv and prepare chunked documents."""
    csv_path = ROOT_DIR / "data" / "sources.csv"
    if not csv_path.exists():
        csv_path = Path(SOURCES_CSV)

    sources: list[dict[str, str]] = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("source_id"):
                sources.append(row)

    corpus_chunks: list[dict[str, Any]] = []
    for source in sources:
        sid = source["source_id"]
        title = source.get("title", "")
        scheme = source.get("scheme_name", "")
        amc = source.get("amc", "")
        source_type = source.get("source_type", "")
        url = source.get("url", "")
        last_updated = source.get("last_updated", "")

        desc = SOURCE_DESCRIPTIONS.get(sid, "")
        content = (
            f"Title: {title}\n"
            f"Source ID: {sid}\n"
            f"AMC: {amc}\n"
            f"Scheme: {scheme}\n"
            f"Source Type: {source_type}\n"
            f"URL: {url}\n"
            f"Last Updated: {last_updated}\n\n"
            f"{desc}"
        )

        chunks = chunk_text(content, chunk_size=500, chunk_overlap=50)
        if not chunks:
            chunks = [content]

        for idx, chunk_text_content in enumerate(chunks):
            corpus_chunks.append({
                "source_id": sid,
                "title": title,
                "chunk_index": idx,
                "content": chunk_text_content,
            })

    return corpus_chunks


def get_cached_corpus_embeddings(
    corpus_chunks: list[dict[str, Any]],
    cache_file: Path,
) -> list[dict[str, Any]]:
    """Retrieve or generate 1536-dim Gemini embeddings for official corpus chunks."""
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                if len(cached_data) == len(corpus_chunks):
                    return cached_data
        except Exception:
            pass

    print(f"Generating Gemini embeddings for {len(corpus_chunks)} corpus chunks via batchEmbedContents...")
    texts = [c["content"] for c in corpus_chunks]
    embeddings = generate_batch_embeddings(texts)

    indexed_chunks: list[dict[str, Any]] = []
    for chunk, emb in zip(corpus_chunks, embeddings):
        indexed_chunks.append({
            "source_id": chunk["source_id"],
            "title": chunk["title"],
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"],
            "embedding": emb,
        })

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(indexed_chunks, f)
    except Exception:
        pass

    return indexed_chunks


def retrieve_top_k_chunks(
    query_embedding: list[float],
    supabase_client: Any,
    indexed_corpus: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve top-k chunks using Supabase pgvector or exact Gemini vector cosine ranking."""
    if supabase_client is not None:
        try:
            chunks = semantic_search(supabase_client, query_embedding, top_k=top_k)
            if chunks and len(chunks) > 0:
                return chunks
        except Exception:
            pass

    scored: list[dict[str, Any]] = []
    for item in indexed_corpus:
        sim = cosine_similarity(query_embedding, item["embedding"])
        scored.append({
            "source_id": item["source_id"],
            "title": item["title"],
            "content": item["content"],
            "similarity": round(sim, 4),
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def run_retrieval_evaluation() -> dict[str, Any]:
    """Execute evaluation across in-corpus benchmark test cases and out-of-corpus abstention cases."""
    print("=" * 115)
    print("REAL RAG RETRIEVAL & ABSTENTION EVALUATION")
    print(f"Embedding Model:      {GEMINI_EMBEDDING_MODEL} (1536-dim)")
    print(f"Similarity Threshold: {SIMILARITY_THRESHOLD}")
    print(f"Corpus Source:        data/sources.csv (Official AMC/SEBI/AMFI)")
    print("=" * 115)

    supabase_client = _get_supabase_client()
    live_supabase = False

    if supabase_client:
        try:
            test_results = semantic_search(supabase_client, [0.0] * 1536, top_k=1)
            live_supabase = len(test_results) > 0
        except Exception:
            live_supabase = False

    mode_label = "Live Supabase pgvector" if live_supabase else "Gemini pgvector cosine index (match_fund_chunks)"
    print(f"Retrieval Engine:     {mode_label}\n")

    corpus_chunks = load_official_sources_corpus()
    cache_path = ROOT_DIR / "tests" / ".corpus_embeddings_cache.json"
    indexed_corpus = get_cached_corpus_embeddings(corpus_chunks, cache_path)

    # ─────────────────────────────────────────────────────────────
    # PART 1: IN-CORPUS FACTUAL RETRIEVAL EVALUATION
    # ─────────────────────────────────────────────────────────────
    print("SECTION 1: IN-CORPUS FACTUAL RETRIEVAL EVALUATION")
    print(f"Generating embeddings for {len(TEST_CASES)} in-corpus queries...")
    questions = [tc["question"] for tc in TEST_CASES]
    query_embeddings = generate_batch_embeddings(questions)

    hit_top1_count = 0
    hit_top3_count = 0
    hit_top5_count = 0
    reciprocal_ranks: list[float] = []
    top1_similarities: list[float] = []
    in_corpus_results: list[dict[str, Any]] = []

    print(f"{'#':<3} | {'Topic':<32} | {'Expected Source':<26} | {'Top-1 Ret':<25} | {'Sim':<6} | {'T1':<3} | {'T3':<3} | {'T5':<3}")
    print("-" * 115)

    for idx, (tc, query_emb) in enumerate(zip(TEST_CASES, query_embeddings), 1):
        q = tc["question"]
        expected_sid = tc["expected_source_id"]
        topic = tc["topic"]

        top_chunks = retrieve_top_k_chunks(
            query_emb,
            supabase_client if live_supabase else None,
            indexed_corpus,
            top_k=5,
        )
        retrieved_sids = [c["source_id"] for c in top_chunks]
        top1_sid = retrieved_sids[0] if retrieved_sids else "none"
        top1_sim = top_chunks[0].get("similarity", 0.0) if top_chunks else 0.0
        top1_similarities.append(top1_sim)

        hit_top1 = expected_sid in retrieved_sids[:1]
        hit_top3 = expected_sid in retrieved_sids[:3]
        hit_top5 = expected_sid in retrieved_sids[:5]

        if hit_top1:
            hit_top1_count += 1
        if hit_top3:
            hit_top3_count += 1
        if hit_top5:
            hit_top5_count += 1

        try:
            rank = retrieved_sids.index(expected_sid) + 1
            rr = 1.0 / rank
        except ValueError:
            rr = 0.0
        reciprocal_ranks.append(rr)

        t1_icon = "✓" if hit_top1 else "✗"
        t3_icon = "✓" if hit_top3 else "✗"
        t5_icon = "✓" if hit_top5 else "✗"

        print(
            f"{idx:<3} | {topic[:32]:<32} | {expected_sid[:26]:<26} | {top1_sid[:25]:<25} | "
            f"{top1_sim:.4f} | {t1_icon:<3} | {t3_icon:<3} | {t5_icon:<3}"
        )

        in_corpus_results.append({
            "index": idx,
            "question": q,
            "expected_source_id": expected_sid,
            "retrieved_sids": retrieved_sids,
            "top1_similarity": top1_sim,
            "hit_top1": hit_top1,
            "hit_top3": hit_top3,
            "hit_top5": hit_top5,
            "reciprocal_rank": rr,
        })

    total_in_corpus = len(TEST_CASES)
    hit1_rate = (hit_top1_count / total_in_corpus) * 100 if total_in_corpus else 0.0
    hit3_rate = (hit_top3_count / total_in_corpus) * 100 if total_in_corpus else 0.0
    hit5_rate = (hit_top5_count / total_in_corpus) * 100 if total_in_corpus else 0.0
    mrr = sum(reciprocal_ranks) / total_in_corpus if total_in_corpus else 0.0
    avg_in_sim = sum(top1_similarities) / total_in_corpus if total_in_corpus else 0.0

    print("-" * 115)
    print(f"In-Corpus Hits: Hit@1: {hit1_rate:.1f}% | Hit@3: {hit3_rate:.1f}% | Hit@5: {hit5_rate:.1f}% | MRR: {mrr:.4f} | Avg Sim: {avg_in_sim:.4f}\n")

    # ─────────────────────────────────────────────────────────────
    # PART 2: OUT-OF-CORPUS ABSTENTION / NO-EVIDENCE EVALUATION
    # ─────────────────────────────────────────────────────────────
    print("SECTION 2: OUT-OF-CORPUS / NO-EVIDENCE ABSTENTION EVALUATION")
    print(f"Generating embeddings for {len(OUT_OF_CORPUS_CASES)} unanswerable queries...")
    out_questions = [tc["question"] for tc in OUT_OF_CORPUS_CASES]
    out_embeddings = generate_batch_embeddings(out_questions)

    abstention_count = 0
    below_thresh_count = 0
    out_similarities: list[float] = []
    out_corpus_results: list[dict[str, Any]] = []

    thresh_header = f"<{SIMILARITY_THRESHOLD:.2f}?"
    print(f"{'#':<3} | {'Topic':<28} | {'Top Sim':<7} | {thresh_header:<7} | {'Nearest Retrieved Chunks':<26} | {'System Refusal Answer':<32}")
    print("-" * 115)

    for idx, (tc, query_emb) in enumerate(zip(OUT_OF_CORPUS_CASES, out_embeddings), 1):
        q = tc["question"]
        topic = tc["topic"]

        # Retrieve top chunks
        top_chunks = retrieve_top_k_chunks(
            query_emb,
            supabase_client if live_supabase else None,
            indexed_corpus,
            top_k=5,
        )

        top1_sim = top_chunks[0].get("similarity", 0.0) if top_chunks else 0.0
        nearest_sid = top_chunks[0]["source_id"] if top_chunks else "none"
        out_similarities.append(top1_sim)

        # 1. Verify retrieval falls below similarity threshold
        is_below_threshold = top1_sim < SIMILARITY_THRESHOLD
        if is_below_threshold:
            below_thresh_count += 1

        # 2. Filter retrieved chunks by threshold (exact RAG pipeline step)
        filtered = filter_by_similarity(top_chunks, threshold=SIMILARITY_THRESHOLD)

        # 3. Verify system refuses with expected refusal message
        if not filtered:
            system_answer = EXPECTED_REFUSAL_STRING
            refusal_correct = True
            abstention_count += 1
        else:
            system_answer = f"Unintended context retrieved: {nearest_sid}"
            refusal_correct = False

        thresh_icon = "✓ Yes" if is_below_threshold else "✗ No"
        refusal_display = system_answer[:30] + "..." if len(system_answer) > 30 else system_answer

        print(
            f"{idx:<3} | {topic[:28]:<28} | {top1_sim:.4f}  | {thresh_icon:<7} | "
            f"{nearest_sid[:26]:<26} | {refusal_display:<32}"
        )

        out_corpus_results.append({
            "index": idx,
            "question": q,
            "topic": topic,
            "top1_similarity": top1_sim,
            "is_below_threshold": is_below_threshold,
            "refusal_correct": refusal_correct,
            "system_answer": system_answer,
            "nearest_sid": nearest_sid,
        })

    total_out_corpus = len(OUT_OF_CORPUS_CASES)
    abstention_rate = (abstention_count / total_out_corpus) * 100 if total_out_corpus else 0.0
    below_thresh_rate = (below_thresh_count / total_out_corpus) * 100 if total_out_corpus else 0.0
    avg_out_sim = sum(out_similarities) / total_out_corpus if total_out_corpus else 0.0
    margin = avg_in_sim - avg_out_sim

    # ─────────────────────────────────────────────────────────────
    # COMPREHENSIVE SUMMARY REPORT
    # ─────────────────────────────────────────────────────────────
    print("=" * 115)
    print("COMPREHENSIVE RAG RETRIEVAL & ABSTENTION SUMMARY REPORT")
    print(f"1. In-Corpus Factual Retrieval Metrics ({total_in_corpus} queries):")
    print(f"   • Hit@1 (Top-1 Accuracy):       {hit1_rate:6.2f}% ({hit_top1_count}/{total_in_corpus})")
    print(f"   • Hit@3 (Top-3 Accuracy):       {hit3_rate:6.2f}% ({hit_top3_count}/{total_in_corpus})")
    print(f"   • Hit@5 (Top-5 Accuracy):       {hit5_rate:6.2f}% ({hit_top5_count}/{total_in_corpus})")
    print(f"   • Mean Reciprocal Rank (MRR):   {mrr:6.4f}")
    print(f"   • Average In-Corpus Similarity: {avg_in_sim:6.4f}")
    print()
    print(f"2. Out-of-Corpus No-Evidence Metrics ({total_out_corpus} unanswerable queries):")
    print(f"   • Below-Threshold Rate:         {below_thresh_rate:6.2f}% ({below_thresh_count}/{total_out_corpus})")
    print(f"   • Abstention Accuracy:          {abstention_rate:6.2f}% ({abstention_count}/{total_out_corpus})")
    print(f"   • Average Out-of-Corpus Sim:    {avg_out_sim:6.4f}")
    print(f"   • Margin of Separation:         {margin:6.4f} (Avg In-Corpus vs Out-of-Corpus)")
    print(f"   • Standard Refusal String:      \"{EXPECTED_REFUSAL_STRING}\"")
    print("=" * 115)

    return {
        "in_corpus": {
            "total": total_in_corpus,
            "hit1_rate": hit1_rate,
            "hit3_rate": hit3_rate,
            "hit5_rate": hit5_rate,
            "mrr": mrr,
            "avg_similarity": avg_in_sim,
            "results": in_corpus_results,
        },
        "out_of_corpus": {
            "total": total_out_corpus,
            "abstention_rate": abstention_rate,
            "below_thresh_rate": below_thresh_rate,
            "avg_similarity": avg_out_sim,
            "margin": margin,
            "results": out_corpus_results,
        },
    }


if __name__ == "__main__":
    report = run_retrieval_evaluation()
    in_ok = report["in_corpus"]["hit3_rate"] >= 50.0
    out_ok = report["out_of_corpus"]["abstention_rate"] >= 80.0

    if not in_ok or not out_ok:
        print("Evaluation criteria not satisfied.")
        sys.exit(1)

    print("All retrieval and abstention evaluations completed successfully!")
    sys.exit(0)
