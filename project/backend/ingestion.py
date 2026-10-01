"""Document ingestion pipeline.

Flow:
  1. Read source metadata from sources.csv.
  2. Extract/clean text content for each source.
  3. Chunk text into ~500-token segments with overlap.
  4. Generate OpenAI embeddings for each chunk.
  5. Store chunks + embeddings + metadata in Supabase pgvector.
"""

from __future__ import annotations
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI
from supabase import create_client, Client

from config import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SOURCES_CSV,
)

MAX_WORDS = 375   # ~500 tokens
OVERLAP_WORDS = 38  # ~50 tokens


@dataclass
class TextChunk:
    chunk_index: int
    content: str
    metadata: dict[str, Any]


def clean_text(text: str) -> str:
    """Remove excessive whitespace, normalize line breaks, strip boilerplate."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s+|\s+$", "", text, flags=re.MULTILINE)
    return text.strip()


def chunk_text(text: str, source_id: str) -> list[TextChunk]:
    """Split text into overlapping chunks on sentence boundaries."""
    if not text or not text.strip():
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_wc = 0
    idx = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        wc = len(sentence.split())

        if current_wc + wc > MAX_WORDS and current:
            content = " ".join(current)
            chunks.append(TextChunk(
                chunk_index=idx,
                content=content,
                metadata={
                    "source_id": source_id,
                    "word_count": current_wc,
                    "char_count": len(content),
                },
            ))
            idx += 1

            # Keep overlap sentences
            keep: list[str] = []
            running = 0
            for s in reversed(current):
                swc = len(s.split())
                if running + swc > OVERLAP_WORDS:
                    break
                keep.insert(0, s)
                running += swc

            current = keep + [sentence]
            current_wc = sum(len(s.split()) for s in current)
        else:
            current.append(sentence)
            current_wc += wc

    if current:
        content = " ".join(current)
        chunks.append(TextChunk(
            chunk_index=idx,
            content=content,
            metadata={
                "source_id": source_id,
                "word_count": current_wc,
                "char_count": len(content),
            },
        ))

    return chunks


# Sample content for each source (in production, fetched from URLs)
SAMPLE_CONTENT: dict[str, str] = {
    "hdfc-balanced-factsheet": (
        "HDFC Balanced Advantage Fund is an open-ended dynamic asset allocation fund. "
        "The expense ratio is 1.50% for the Regular Plan and 0.85% for the Direct Plan. "
        "The benchmark is Nifty 50 Hybrid Composite Debt 50:50 Index. "
        "The minimum SIP amount is Rs. 100 per installment. "
        "Exit load is 1% if redeemed within 90 days. "
        "The fund is rated Moderately High Risk on the SEBI Riskometer. "
        "There is no lock-in period."
    ),
    "hdfc-balanced-sid": (
        "HDFC Balanced Advantage Fund Scheme Information Document. "
        "This is an open-ended dynamic asset allocation fund. "
        "The minimum application amount is Rs. 5,000. "
        "The minimum SIP amount is Rs. 100. "
        "Exit load of 1% applies if units are redeemed within 90 days of allotment. "
        "No lock-in period. "
        "The scheme aims to generate returns through dynamic allocation between equity and debt."
    ),
    "hdfc-balanced-kim": (
        "HDFC Balanced Advantage Fund Key Information Memorandum. "
        "Riskometer rating: Moderately High Risk. "
        "The fund dynamically allocates between equity and debt. "
        "Benchmark: Nifty 50 Hybrid Composite Debt 50:50 Index. "
        "No lock-in period. Exit load: 1% within 90 days."
    ),
    "hdfc-balanced-portfolio": (
        "HDFC Balanced Advantage Fund Portfolio Statement. "
        "The fund maintains a dynamic allocation between equity and debt instruments. "
        "Equity allocation typically ranges between 30-80% depending on market conditions. "
        "The portfolio is rebalanced based on the fund manager's assessment of market valuations."
    ),
    "hdfc-balanced-addendum": (
        "HDFC Balanced Advantage Fund Addendum. "
        "No changes to expense ratio or exit load. "
        "The fund continues to operate as an open-ended dynamic asset allocation scheme."
    ),
    "hdfc-midcap-factsheet": (
        "HDFC Mid-Cap Opportunities Fund is an open-ended equity scheme. "
        "The expense ratio is 1.75% for the Regular Plan and 1.05% for the Direct Plan. "
        "The benchmark is Nifty Midcap 150 TRI. "
        "The minimum SIP amount is Rs. 100 per installment. "
        "Exit load is 1% if redeemed within 365 days. "
        "The fund is rated High Risk on the SEBI Riskometer. No lock-in period."
    ),
    "hdfc-midcap-sid": (
        "HDFC Mid-Cap Opportunities Fund Scheme Information Document. "
        "Open-ended mid-cap equity scheme. "
        "Minimum application amount: Rs. 5,000. Minimum SIP: Rs. 100. "
        "Exit load: 1% within 365 days. No lock-in period. "
        "The fund invests predominantly in mid-cap stocks."
    ),
    "hdfc-midcap-kim": (
        "HDFC Mid-Cap Opportunities Fund Key Information Memorandum. "
        "Riskometer rating: High Risk. "
        "The fund invests in mid-cap stocks which carry higher volatility. "
        "Benchmark: Nifty Midcap 150 TRI. No lock-in period. "
        "Exit load: 1% within 365 days."
    ),
    "hdfc-midcap-portfolio": (
        "HDFC Mid-Cap Opportunities Fund Portfolio Statement. "
        "The fund invests predominantly in mid-cap companies across various sectors. "
        "The portfolio typically holds 40-60 mid-cap stocks. "
        "Sector allocation is diversified across manufacturing, financials, healthcare, and technology."
    ),
    "hdfc-midcap-addendum": (
        "HDFC Mid-Cap Opportunities Fund Addendum. "
        "No changes to expense ratio or exit load. "
        "The fund continues as an open-ended mid-cap equity scheme."
    ),
    "hdfc-shortterm-factsheet": (
        "HDFC Short Term Debt Fund is an open-ended debt scheme. "
        "The expense ratio is 0.85% for the Regular Plan and 0.45% for the Direct Plan. "
        "The benchmark is NIFTY Short Duration Debt Index. "
        "The minimum SIP amount is Rs. 1,000 per installment. "
        "Exit load is 0.50% if redeemed within 3 months. "
        "The fund is rated Low to Moderate Risk on the SEBI Riskometer. No lock-in period."
    ),
    "hdfc-shortterm-sid": (
        "HDFC Short Term Debt Fund Scheme Information Document. "
        "Open-ended short-duration debt scheme. "
        "Minimum application amount: Rs. 5,000. Minimum SIP: Rs. 1,000. "
        "Exit load: 0.50% within 3 months. No lock-in period. "
        "The fund invests in short-term debt securities."
    ),
    "hdfc-shortterm-kim": (
        "HDFC Short Term Debt Fund Key Information Memorandum. "
        "Riskometer rating: Low to Moderate Risk. "
        "The fund invests in short-duration debt instruments. "
        "Benchmark: NIFTY Short Duration Debt Index. No lock-in period. "
        "Exit load: 0.50% within 3 months."
    ),
    "hdfc-shortterm-portfolio": (
        "HDFC Short Term Debt Fund Portfolio Statement. "
        "The fund invests in short-term corporate bonds, commercial papers, and government securities. "
        "The portfolio maintains a modified duration of 1-3 years. "
        "Credit quality is predominantly AAA rated."
    ),
    "hdfc-index-factsheet": (
        "HDFC Index Fund - Nifty 50 Plan is an open-ended index equity scheme. "
        "The expense ratio is 0.40% for the Regular Plan and 0.20% for the Direct Plan. "
        "The benchmark is NIFTY 50 TRI. "
        "The minimum SIP amount is Rs. 100 per installment. "
        "Exit load is 0.50% if redeemed within 30 days. "
        "The fund is rated Very High Risk on the SEBI Riskometer. No lock-in period."
    ),
    "hdfc-index-sid": (
        "HDFC Index Fund - Nifty 50 Plan Scheme Information Document. "
        "Open-ended index fund replicating the Nifty 50 index. "
        "Minimum application amount: Rs. 5,000. Minimum SIP: Rs. 100. "
        "Exit load: 0.50% within 30 days. No lock-in period. "
        "The fund passively tracks the Nifty 50 index."
    ),
    "hdfc-index-kim": (
        "HDFC Index Fund - Nifty 50 Plan Key Information Memorandum. "
        "Riskometer rating: Very High Risk. "
        "The fund replicates the Nifty 50 index. "
        "Benchmark: NIFTY 50 TRI. No lock-in period. "
        "Exit load: 0.50% within 30 days."
    ),
    "hdfc-index-portfolio": (
        "HDFC Index Fund - Nifty 50 Plan Portfolio Statement. "
        "The fund holds all 50 stocks of the Nifty 50 index in the same proportion as the index. "
        "The portfolio mirrors the index composition with minimal tracking error."
    ),
    "sebi-circular-mutual-funds": (
        "SEBI Circular on Mutual Fund Regulations. "
        "This circular outlines the regulatory framework for mutual funds in India "
        "including classification of schemes, expense ratio limits, and disclosure requirements. "
        "All AMCs must comply with SEBI regulations for scheme launch, operation, and winding up."
    ),
    "sebi-circular-ter": (
        "SEBI Circular on Total Expense Ratio. "
        "SEBI has prescribed maximum expense ratio limits for various categories of mutual fund schemes. "
        "The TER includes management fee and other recurring expenses. "
        "AMCs must disclose the TER for each scheme on their website and in factsheets."
    ),
    "sebi-riskometer": (
        "SEBI Riskometer Guidelines. "
        "The SEBI Riskometer is a graphical representation of the risk level of a mutual fund scheme. "
        "Risk levels range from Low Risk to Very High Risk. "
        "All schemes must display the Riskometer rating prominently in their factsheets and KIMs."
    ),
    "amfi-scheme-codes": (
        "AMFI Scheme Code Master List. "
        "AMFI maintains a master list of all mutual fund schemes with unique scheme codes. "
        "This list is updated regularly and serves as the reference for all AMCs, distributors, and platforms."
    ),
    "amfi-total-expense-ratio": (
        "AMFI Total Expense Ratio Disclosure. "
        "AMFI publishes the TER for all mutual fund schemes on its website. "
        "This data is updated daily and includes both Regular and Direct Plan expense ratios for all schemes."
    ),
    "amfi-nav-history": (
        "AMFI NAV History Database. "
        "AMFI maintains historical NAV data for all mutual fund schemes. "
        "This data is used for performance calculation and is available on the AMFI website."
    ),
}


def get_source_content(source_id: str, title: str, amc: str) -> str:
    """Extract text content for a source. In production, fetches from URL."""
    return SAMPLE_CONTENT.get(source_id, f"{title}. This is an official source document from {amc}.")


def run_ingestion(sources_csv_path: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Run the full ingestion pipeline.

    Returns a summary dict with counts.
    """
    csv_path = sources_csv_path or SOURCES_CSV
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not set. Set it in .env or environment."}
    if not dry_run and not SUPABASE_SERVICE_KEY:
        return {"error": "SUPABASE_SERVICE_ROLE_KEY not set."}

    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    supabase: Client | None = None
    if not dry_run:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    csv_full_path = Path(csv_path)
    if not csv_full_path.is_absolute():
        csv_full_path = Path(__file__).resolve().parent.parent / csv_path

    with open(csv_full_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sources = list(reader)

    total_chunks = 0
    total_embeddings = 0
    ingested_sources: list[str] = []

    for src in sources:
        source_id = src["source_id"]
        title = src["title"]
        amc = src["amc"]

        # 1. Extract and clean text
        raw = get_source_content(source_id, title, amc)
        text = clean_text(raw)

        # 2. Chunk
        chunks = chunk_text(text, source_id)

        # 3. Store source metadata
        if not dry_run and supabase:
            supabase.table("fund_sources").upsert({
                "source_id": source_id,
                "amc": amc,
                "scheme_name": src.get("scheme_name", ""),
                "source_type": src["source_type"],
                "url": src["url"],
                "title": title,
                "last_updated": src.get("last_updated", ""),
            }).execute()

            # 4. Delete old chunks for this source
            supabase.table("fund_chunks").delete().eq("source_id", source_id).execute()

        # 5. Generate embeddings and store
        for chunk in chunks:
            if not dry_run and supabase and openai_client:
                try:
                    resp = openai_client.embeddings.create(
                        model=OPENAI_EMBEDDING_MODEL,
                        input=chunk.content,
                    )
                    embedding = resp.data[0].embedding
                    total_embeddings += 1

                    supabase.table("fund_chunks").insert({
                        "source_id": source_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "embedding": embedding,
                        "metadata": json.dumps(chunk.metadata),
                    }).execute()
                except Exception:
                    pass

        total_chunks += len(chunks)
        ingested_sources.append(source_id)

    return {
        "sources_ingested": len(ingested_sources),
        "total_chunks": total_chunks,
        "total_embeddings": total_embeddings,
        "source_ids": ingested_sources,
        "dry_run": dry_run,
    }
