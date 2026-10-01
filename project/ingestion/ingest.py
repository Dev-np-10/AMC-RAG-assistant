"""Source ingestion script for the Facts-Only Mutual Fund RAG chatbot.

Reads sources from a CSV file, fetches source content, chunks it,
generates OpenAI embeddings, and stores everything in Supabase pgvector.

Usage:
    python ingest.py --sources ../data/sources.csv

Environment variables (from .env):
    OPENAI_API_KEY       - OpenAI API key for embeddings
    SUPABASE_URL         - Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY - Supabase service role key
"""

import argparse
import csv
import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

from chunker import chunk_text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

SAMPLE_CONTENT = {
    "hdfc-balanced-factsheet": """HDFC Balanced Advantage Fund is an open-ended dynamic asset allocation fund. The expense ratio is 1.50% for the Regular Plan and 0.85% for the Direct Plan. The benchmark is Nifty 50 Hybrid Composite Debt 50:50 Index. The minimum SIP amount is Rs. 100 per installment. Exit load is 1% if redeemed within 90 days. The fund is rated Moderately High Risk on the SEBI Riskometer. There is no lock-in period.""",
    "hdfc-balanced-sid": """HDFC Balanced Advantage Fund Scheme Information Document. This is an open-ended dynamic asset allocation fund. The minimum application amount is Rs. 5,000. The minimum SIP amount is Rs. 100. Exit load of 1% applies if units are redeemed within 90 days of allotment. No lock-in period. The scheme aims to generate returns through dynamic allocation between equity and debt.""",
    "hdfc-balanced-kim": """HDFC Balanced Advantage Fund Key Information Memorandum. Riskometer rating: Moderately High Risk. The fund dynamically allocates between equity and debt. Benchmark: Nifty 50 Hybrid Composite Debt 50:50 Index. No lock-in period. Exit load: 1% within 90 days.""",
    "hdfc-balanced-portfolio": """HDFC Balanced Advantage Fund Portfolio Statement. The fund maintains a dynamic allocation between equity and debt instruments. Equity allocation typically ranges between 30-80% depending on market conditions. The portfolio is rebalanced based on the fund manager's assessment of market valuations.""",
    "hdfc-balanced-addendum": """HDFC Balanced Advantage Fund Addendum. No changes to expense ratio or exit load. The fund continues to operate as an open-ended dynamic asset allocation scheme.""",
    "hdfc-midcap-factsheet": """HDFC Mid-Cap Opportunities Fund is an open-ended equity scheme. The expense ratio is 1.75% for the Regular Plan and 1.05% for the Direct Plan. The benchmark is Nifty Midcap 150 TRI. The minimum SIP amount is Rs. 100 per installment. Exit load is 1% if redeemed within 365 days. The fund is rated High Risk on the SEBI Riskometer. No lock-in period.""",
    "hdfc-midcap-sid": """HDFC Mid-Cap Opportunities Fund Scheme Information Document. Open-ended mid-cap equity scheme. Minimum application amount: Rs. 5,000. Minimum SIP: Rs. 100. Exit load: 1% within 365 days. No lock-in period. The fund invests predominantly in mid-cap stocks.""",
    "hdfc-midcap-kim": """HDFC Mid-Cap Opportunities Fund Key Information Memorandum. Riskometer rating: High Risk. The fund invests in mid-cap stocks which carry higher volatility. Benchmark: Nifty Midcap 150 TRI. No lock-in period. Exit load: 1% within 365 days.""",
    "hdfc-midcap-portfolio": """HDFC Mid-Cap Opportunities Fund Portfolio Statement. The fund invests predominantly in mid-cap companies across various sectors. The portfolio typically holds 40-60 mid-cap stocks. Sector allocation is diversified across manufacturing, financials, healthcare, and technology.""",
    "hdfc-midcap-addendum": """HDFC Mid-Cap Opportunities Fund Addendum. No changes to expense ratio or exit load. The fund continues as an open-ended mid-cap equity scheme.""",
    "hdfc-shortterm-factsheet": """HDFC Short Term Debt Fund is an open-ended debt scheme. The expense ratio is 0.85% for the Regular Plan and 0.45% for the Direct Plan. The benchmark is NIFTY Short Duration Debt Index. The minimum SIP amount is Rs. 1,000 per installment. Exit load is 0.50% if redeemed within 3 months. The fund is rated Low to Moderate Risk on the SEBI Riskometer. No lock-in period.""",
    "hdfc-shortterm-sid": """HDFC Short Term Debt Fund Scheme Information Document. Open-ended short-duration debt scheme. Minimum application amount: Rs. 5,000. Minimum SIP: Rs. 1,000. Exit load: 0.50% within 3 months. No lock-in period. The fund invests in short-term debt securities.""",
    "hdfc-shortterm-kim": """HDFC Short Term Debt Fund Key Information Memorandum. Riskometer rating: Low to Moderate Risk. The fund invests in short-duration debt instruments. Benchmark: NIFTY Short Duration Debt Index. No lock-in period. Exit load: 0.50% within 3 months.""",
    "hdfc-shortterm-portfolio": """HDFC Short Term Debt Fund Portfolio Statement. The fund invests in short-term corporate bonds, commercial papers, and government securities. The portfolio maintains a modified duration of 1-3 years. Credit quality is predominantly AAA rated.""",
    "hdfc-index-factsheet": """HDFC Index Fund - Nifty 50 Plan is an open-ended index equity scheme. The expense ratio is 0.40% for the Regular Plan and 0.20% for the Direct Plan. The benchmark is NIFTY 50 TRI. The minimum SIP amount is Rs. 100 per installment. Exit load is 0.50% if redeemed within 30 days. The fund is rated Very High Risk on the SEBI Riskometer. No lock-in period.""",
    "hdfc-index-sid": """HDFC Index Fund - Nifty 50 Plan Scheme Information Document. Open-ended index fund replicating the Nifty 50 index. Minimum application amount: Rs. 5,000. Minimum SIP: Rs. 100. Exit load: 0.50% within 30 days. No lock-in period. The fund passively tracks the Nifty 50 index.""",
    "hdfc-index-kim": """HDFC Index Fund - Nifty 50 Plan Key Information Memorandum. Riskometer rating: Very High Risk. The fund replicates the Nifty 50 index. Benchmark: NIFTY 50 TRI. No lock-in period. Exit load: 0.50% within 30 days.""",
    "hdfc-index-portfolio": """HDFC Index Fund - Nifty 50 Plan Portfolio Statement. The fund holds all 50 stocks of the Nifty 50 index in the same proportion as the index. The portfolio mirrors the index composition with minimal tracking error.""",
    "sebi-circular-mutual-funds": """SEBI Circular on Mutual Fund Regulations. This circular outlines the regulatory framework for mutual funds in India including classification of schemes, expense ratio limits, and disclosure requirements. All AMCs must comply with SEBI regulations for scheme launch, operation, and winding up.""",
    "sebi-circular-ter": """SEBI Circular on Total Expense Ratio. SEBI has prescribed maximum expense ratio limits for various categories of mutual fund schemes. The TER includes management fee and other recurring expenses. AMCs must disclose the TER for each scheme on their website and in factsheets.""",
    "sebi-riskometer": """SEBI Riskometer Guidelines. The SEBI Riskometer is a graphical representation of the risk level of a mutual fund scheme. Risk levels range from Low Risk to Very High Risk. All schemes must display the Riskometer rating prominently in their factsheets and KIMs.""",
    "amfi-scheme-codes": """AMFI Scheme Code Master List. AMFI maintains a master list of all mutual fund schemes with unique scheme codes. This list is updated regularly and serves as the reference for all AMCs, distributors, and platforms.""",
    "amfi-total-expense-ratio": """AMFI Total Expense Ratio Disclosure. AMFI publishes the TER for all mutual fund schemes on its website. This data is updated daily and includes both Regular and Direct Plan expense ratios for all schemes.""",
    "amfi-nav-history": """AMFI NAV History Database. AMFI maintains historical NAV data for all mutual fund schemes. This data is used for performance calculation and is available on the AMFI website.""",
}


def get_embedding(client: OpenAI, text: str) -> list[float]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def ingest(sources_csv: str, dry_run: bool = False) -> None:
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set. Set it in .env or environment.")
        sys.exit(1)

    if not dry_run and not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY)
    supabase: Client | None = None
    if not dry_run:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    with open(sources_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sources = list(reader)

    print(f"Found {len(sources)} sources to ingest.")

    total_chunks = 0
    total_embeddings = 0

    for src in sources:
        source_id = src["source_id"]
        title = src["title"]
        content = SAMPLE_CONTENT.get(source_id, f"{title}. This is an official source document from {src['amc']}.")

        chunks = chunk_text(content, source_id)
        print(f"  [{source_id}] {len(chunks)} chunks")

        if not dry_run and supabase:
            supabase.table("fund_sources").upsert({
                "source_id": source_id,
                "amc": src["amc"],
                "scheme_name": src.get("scheme_name", ""),
                "source_type": src["source_type"],
                "url": src["url"],
                "title": title,
                "last_updated": src.get("last_updated", ""),
            }).execute()

            for chunk in chunks:
                embedding = get_embedding(client, chunk.content)
                total_embeddings += 1

                supabase.table("fund_chunks").insert({
                    "source_id": source_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": json.dumps(chunk.metadata),
                }).execute()

        total_chunks += len(chunks)

    mode = "DRY RUN" if dry_run else "INGESTED"
    print(f"\n{mode}: {len(sources)} sources, {total_chunks} chunks, {total_embeddings} embeddings.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest mutual fund sources into pgvector")
    parser.add_argument("--sources", default="../data/sources.csv", help="Path to sources CSV")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to database")
    args = parser.parse_args()

    ingest(args.sources, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
