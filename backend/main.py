"""FastAPI application — Facts-Only Mutual Fund RAG Chatbot API.

Endpoints:
  POST   /api/chat     — classify + answer a question
  POST   /api/ingest   — run document ingestion pipeline
  GET    /api/sources  — list all ingested sources
  GET    /api/health   — health check
"""

from __future__ import annotations
from datetime import date
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from classifier import classify_query, QueryCategory
from rag import run_rag
from ingestion import run_ingestion
from config import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY

app = FastAPI(
    title="Facts-Only Mutual Fund RAG Chatbot API",
    description="Retrieval-augmented generation chatbot for factual mutual fund questions from official AMC/SEBI/AMFI sources.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Client-Info", "Apikey"],
)


# ── Request / Response models ─────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class Citation(BaseModel):
    source_id: str
    title: str
    url: str
    amc: str
    scheme_name: str
    last_updated: str


class ChatResponse(BaseModel):
    answer: str
    citation: Citation | None = None
    last_updated: str | None = None
    refused: bool = False
    refusal_reason: str | None = None
    category: str


class IngestRequest(BaseModel):
    sources_csv: str | None = None
    dry_run: bool = False


class IngestResponse(BaseModel):
    sources_ingested: int
    total_chunks: int
    total_embeddings: int
    source_ids: list[str]
    dry_run: bool
    error: str | None = None


class SourceItem(BaseModel):
    source_id: str
    amc: str
    scheme_name: str | None
    source_type: str
    url: str
    title: str
    last_updated: str | None


class HealthResponse(BaseModel):
    status: str
    openai_configured: bool
    supabase_configured: bool
    date: str


# ── Endpoints ─────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Classify a question and return a factual, grounded answer or a refusal.

    Classification flow:
      1. PII           → block immediately, no retrieval.
      2. ADVICE        → refuse with explanation.
      3. PERFORMANCE   → refuse with explanation.
      4. FACTUAL       → run RAG pipeline (embed → search → LLM → citation).
      5. OUT_OF_SCOPE  → refuse with explanation.
    """
    question = req.question.strip()

    # 1. Classify the query
    result = classify_query(question)

    # 2. Handle non-factual categories — refuse without retrieval
    if result.category == QueryCategory.PII:
        return ChatResponse(
            answer=result.reason,
            citation=None,
            last_updated=None,
            refused=True,
            refusal_reason=result.reason,
            category=result.category.value,
        )

    if result.category == QueryCategory.ADVICE:
        return ChatResponse(
            answer=result.reason,
            citation=None,
            last_updated=None,
            refused=True,
            refusal_reason=result.reason,
            category=result.category.value,
        )

    if result.category == QueryCategory.PERFORMANCE:
        return ChatResponse(
            answer=result.reason,
            citation=None,
            last_updated=None,
            refused=True,
            refusal_reason=result.reason,
            category=result.category.value,
        )

    if result.category == QueryCategory.OUT_OF_SCOPE:
        return ChatResponse(
            answer=result.reason,
            citation=None,
            last_updated=None,
            refused=True,
            refusal_reason=result.reason,
            category=result.category.value,
        )

    # 3. FACTUAL — run the RAG pipeline
    rag_result = run_rag(question)

    citation: Citation | None = None
    if rag_result.get("citation"):
        c = rag_result["citation"]
        citation = Citation(
            source_id=c["source_id"],
            title=c["title"],
            url=c["url"],
            amc=c["amc"],
            scheme_name=c.get("scheme_name", ""),
            last_updated=c.get("last_updated", ""),
        )

    return ChatResponse(
        answer=rag_result["answer"],
        citation=citation,
        last_updated=rag_result.get("last_updated"),
        refused=rag_result.get("refused", False),
        refusal_reason=rag_result.get("refusal_reason"),
        category=rag_result.get("category", "FACTUAL"),
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest) -> IngestResponse:
    """Run the document ingestion pipeline.

    Reads sources from CSV, extracts/cleans text, chunks it, generates
    OpenAI embeddings, and stores everything in Supabase pgvector.
    """
    result = run_ingestion(
        sources_csv_path=req.sources_csv,
        dry_run=req.dry_run,
    )

    if "error" in result:
        return IngestResponse(
            sources_ingested=0,
            total_chunks=0,
            total_embeddings=0,
            source_ids=[],
            dry_run=req.dry_run,
            error=result["error"],
        )

    return IngestResponse(
        sources_ingested=result["sources_ingested"],
        total_chunks=result["total_chunks"],
        total_embeddings=result["total_embeddings"],
        source_ids=result["source_ids"],
        dry_run=result["dry_run"],
    )


@app.get("/api/sources", response_model=list[SourceItem])
async def get_sources() -> list[SourceItem]:
    """List all ingested sources with metadata."""
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return []

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = (
            supabase.table("fund_sources")
            .select("source_id, amc, scheme_name, source_type, url, title, last_updated")
            .order("source_id")
            .execute()
        )
        items: list[SourceItem] = []
        for row in result.data or []:
            items.append(SourceItem(
                source_id=row["source_id"],
                amc=row["amc"],
                scheme_name=row.get("scheme_name"),
                source_type=row["source_type"],
                url=row["url"],
                title=row["title"],
                last_updated=row.get("last_updated"),
            ))
        return items
    except Exception:
        return []


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check — reports whether OpenAI and Supabase are configured."""
    return HealthResponse(
        status="ok",
        openai_configured=bool(OPENAI_API_KEY),
        supabase_configured=bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
        date=date.today().isoformat(),
    )
