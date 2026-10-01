"""RAG pipeline — embeddings, semantic retrieval, prompt construction, LLM generation, citation extraction.

Flow:
  1. Generate OpenAI embedding for the user question.
  2. Call Supabase RPC `match_fund_chunks` for top-k semantic search.
  3. Filter by similarity threshold — refuse if no evidence.
  4. Build a grounded prompt with retrieved context.
  5. Call OpenAI LLM with strict system instructions.
  6. Extract exactly one citation from the top retrieved chunk's source metadata.
"""

from __future__ import annotations
from typing import Any
from openai import OpenAI
from supabase import create_client, Client

from config import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_LLM_MODEL,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SIMILARITY_THRESHOLD,
    TOP_K,
)

SYSTEM_PROMPT = """\
You are a facts-only mutual fund chatbot. Answer the user's question using ONLY \
the provided context from official sources.

Rules:
1. Answer in 3 sentences or fewer.
2. State only facts from the context — no opinions, advice, or predictions.
3. Do not compare funds or recommend investments.
4. If the context does not contain the answer, say: \
"I could not find this information in the available sources."
5. Do not mention the context or source by name in the answer — just state the facts.
6. Do not include any disclaimer or caveat — the system handles that separately.\
"""


def _get_clients() -> tuple[OpenAI | None, Client | None]:
    """Build OpenAI and Supabase clients. Returns (None, None) if keys are missing."""
    openai_client: OpenAI | None = None
    supabase_client: Client | None = None

    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    return openai_client, supabase_client


def generate_embedding(text: str, client: OpenAI) -> list[float] | None:
    """Generate an OpenAI embedding for the given text."""
    try:
        resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=text)
        return resp.data[0].embedding
    except Exception:
        return None


def semantic_search(
    supabase: Client,
    query_embedding: list[float],
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Call the `match_fund_chunks` RPC and return matching chunks with metadata."""
    try:
        result = supabase.rpc(
            "match_fund_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
            },
        ).execute()
        return result.data or []
    except Exception:
        return []


def filter_by_similarity(
    chunks: list[dict[str, Any]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Keep only chunks above the similarity threshold."""
    return [c for c in chunks if c.get("similarity", 0) >= threshold]


def build_context(chunks: list[dict[str, Any]]) -> str:
    """Build a text context string from the top retrieved chunks."""
    return "\n\n".join(c["content"] for c in chunks[:3])


def generate_answer(
    question: str,
    context: str,
    citation_title: str,
    client: OpenAI,
) -> str | None:
    """Call the OpenAI LLM to generate a grounded answer."""
    try:
        resp = client.chat.completions.create(
            model=OPENAI_LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context from {citation_title}:\n\n{context}\n\nQuestion: {question}",
                },
            ],
            temperature=0,
            max_tokens=150,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def extract_citation(
    supabase: Client,
    source_id: str,
) -> dict[str, Any] | None:
    """Fetch source metadata (URL, title, AMC, scheme, last-updated) for a citation."""
    try:
        result = (
            supabase.table("fund_sources")
            .select("source_id, title, url, amc, scheme_name, last_updated")
            .eq("source_id", source_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None
    except Exception:
        return None


def run_rag(question: str) -> dict[str, Any]:
    """Full RAG pipeline. Returns a dict with answer, citation, last_updated, refused.

    Returns:
        {
            "answer": str,
            "citation": dict | None,
            "last_updated": str | None,
            "refused": bool,
            "refusal_reason": str | None,
            "category": "FACTUAL",
        }
    """
    openai_client, supabase_client = _get_clients()

    # If no backend clients are configured, signal "no evidence"
    if not openai_client or not supabase_client:
        return {
            "answer": "I could not find any factual information about this in the ingested sources. "
            "Please try asking about expense ratio, SIP, exit load, lock-in period, "
            "riskometer, or benchmark for any of the four HDFC schemes covered.",
            "citation": None,
            "last_updated": None,
            "refused": False,
            "refusal_reason": None,
            "category": "FACTUAL",
        }

    # 1. Generate embedding
    embedding = generate_embedding(question, openai_client)
    if not embedding:
        return {
            "answer": "I could not generate a search embedding for your question. "
            "Please ensure the OpenAI API key is configured and try again.",
            "citation": None,
            "last_updated": None,
            "refused": False,
            "refusal_reason": None,
            "category": "FACTUAL",
        }

    # 2. Semantic search
    chunks = semantic_search(supabase_client, embedding)
    if not chunks:
        return {
            "answer": "I could not find any factual information about this in the ingested sources. "
            "Please try asking about expense ratio, SIP, exit load, lock-in period, "
            "riskometer, or benchmark for any of the four HDFC schemes covered.",
            "citation": None,
            "last_updated": None,
            "refused": False,
            "refusal_reason": None,
            "category": "FACTUAL",
        }

    # 3. Filter by similarity — never answer without supporting evidence
    relevant = filter_by_similarity(chunks)
    if not relevant:
        return {
            "answer": "I could not find any factual information about this in the ingested sources. "
            "Please try asking about expense ratio, SIP, exit load, lock-in period, "
            "riskometer, or benchmark for any of the four HDFC schemes covered.",
            "citation": None,
            "last_updated": None,
            "refused": False,
            "refusal_reason": None,
            "category": "FACTUAL",
        }

    # 4. Build context and get citation from top chunk
    top_chunk = relevant[0]
    context = build_context(relevant)
    citation_data = extract_citation(supabase_client, top_chunk["source_id"])

    citation: dict[str, Any] | None = None
    last_updated: str | None = None
    citation_title = top_chunk["source_id"]

    if citation_data:
        citation = {
            "source_id": citation_data["source_id"],
            "title": citation_data["title"],
            "url": citation_data["url"],
            "amc": citation_data["amc"],
            "scheme_name": citation_data.get("scheme_name") or "",
            "last_updated": citation_data.get("last_updated") or "",
        }
        last_updated = citation["last_updated"]
        citation_title = citation["title"]

    # 5. Generate LLM answer
    answer = generate_answer(question, context, citation_title, openai_client)

    # Fallback: use top chunk content directly if LLM fails
    if not answer:
        answer = top_chunk["content"][:500]

    return {
        "answer": answer,
        "citation": citation,
        "last_updated": last_updated,
        "refused": False,
        "refusal_reason": None,
        "category": "FACTUAL",
    }
