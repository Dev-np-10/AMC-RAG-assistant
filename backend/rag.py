"""RAG pipeline — embeddings, semantic retrieval, prompt construction, Gemini LLM generation, citation extraction.

Flow:
  1. Generate Gemini embedding for the user question (gemini-embedding-2-preview, 1536-dim).
  2. Call Supabase RPC `match_fund_chunks` for top-k semantic search.
  3. Filter by similarity threshold — refuse if no evidence.
  4. Build indexed context with source numbers [Source 1], [Source 2], etc.
  5. Call Google Gemini LLM (gemini-3.8-flash) instructing it to return the supporting source index.
  6. Validate the supporting source index and select the corresponding retrieved chunk.
  7. Extract the final citation metadata from the supporting chunk's source_id.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_LLM_MODEL,
    SIMILARITY_THRESHOLD,
    SOURCES_CSV,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
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
6. Do not include any disclaimer or caveat — the system handles that separately.
7. On a new line at the very end of your response, specify which retrieved source directly supported your answer:
Source: [N]
where N is the integer index (1, 2, 3...) of the supporting [Source N]. If no source supports the answer, omit this line.\
"""


def _get_supabase_client() -> Any | None:
    """Initialize Supabase client if credentials are configured."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    try:
        from supabase import create_client

        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception:
        return None


def generate_embedding(
    text: str,
    api_key: str = GEMINI_API_KEY,
    model: str = GEMINI_EMBEDDING_MODEL,
    retries: int = 3,
) -> list[float] | None:
    """Generate a 1536-dim embedding using Google Gemini API."""
    if not api_key or not text:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    )
    payload = {
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 1536,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "aistudio-build",
    }

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("embedding", {}).get("values")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            return None

    return None


def semantic_search_rest(
    query_embedding: list[float],
    supabase_url: str = SUPABASE_URL,
    service_key: str = SUPABASE_SERVICE_KEY,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Query match_fund_chunks RPC via direct Supabase PostgREST endpoint."""
    if not supabase_url or not service_key:
        return []
    url = f"{supabase_url.rstrip('/')}/rest/v1/rpc/match_fund_chunks"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "query_embedding": query_embedding,
        "match_count": top_k,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        return []


def semantic_search(
    supabase: Any,
    query_embedding: list[float],
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Call the `match_fund_chunks` RPC and return matching chunks with metadata."""
    if supabase and hasattr(supabase, "rpc"):
        try:
            result = supabase.rpc(
                "match_fund_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k,
                },
            ).execute()
            if result.data:
                return result.data
        except Exception:
            pass

    return semantic_search_rest(query_embedding, top_k=top_k)


def filter_by_similarity(
    chunks: list[dict[str, Any]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Keep only chunks above the similarity threshold."""
    return [c for c in chunks if c.get("similarity", 0) >= threshold]


def build_context(chunks: list[dict[str, Any]]) -> str:
    """Build an indexed text context string from retrieved chunks.

    Each chunk is labeled with [Source 1], [Source 2], etc. so the LLM can reference it.
    """
    formatted_chunks = []
    for idx, c in enumerate(chunks[:TOP_K], start=1):
        source_id = c.get("source_id", "")
        content = c.get("content", "").strip()
        header = f"[Source {idx}] ({source_id})" if source_id else f"[Source {idx}]"
        formatted_chunks.append(f"{header}:\n{content}")
    return "\n\n".join(formatted_chunks)


def parse_answer_and_source_index(
    raw_output: str,
    max_sources: int,
) -> tuple[str, int | None]:
    """Extract clean answer text and validate the supporting source index (1-based).

    Returns:
        (clean_answer, validated_source_index or None)
    """
    if not raw_output:
        return "", None

    text = raw_output.strip()
    source_index: int | None = None

    # Check for JSON format first
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            ans = str(data.get("answer", "")).strip()
            idx = data.get("source_index")
            if isinstance(idx, int) and 1 <= idx <= max_sources:
                return ans, idx
            return ans, None
        except Exception:
            pass

    # Look for trailing "Source: [N]" or "Source: N"
    source_patterns = [
        r"(?i)\n*(?:supporting\s+source|source|source_index)\s*[:=\[]\s*\[?(\d+)\]?",
        r"(?i)\[source\s*(\d+)\]\s*$",
    ]

    for pat in source_patterns:
        match = re.search(pat, text)
        if match:
            try:
                candidate_idx = int(match.group(1))
                if 1 <= candidate_idx <= max_sources:
                    source_index = candidate_idx
                # Strip the source reference tag from the user-facing answer
                text = text[: match.start()].strip()
                break
            except Exception:
                pass

    # Clean any trailing "Source:" label leftovers or empty lines
    text = re.sub(r"(?i)\n+source:\s*$", "", text).strip()

    return text, source_index


def generate_answer(
    question: str,
    context: str,
    max_sources: int,
    api_key: str = GEMINI_API_KEY,
    model: str = GEMINI_LLM_MODEL,
    retries: int = 2,
) -> tuple[str | None, int | None]:
    """Call Google Gemini LLM to generate a grounded answer with supporting source index."""
    if not api_key:
        return None, None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    )
    prompt_text = f"Context from official sources:\n\n{context}\n\nQuestion: {question}"

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 250,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "aistudio-build",
    }

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        raw_text = parts[0]["text"].strip()
                        clean_answer, source_idx = parse_answer_and_source_index(
                            raw_text, max_sources
                        )
                        return clean_answer, source_idx
                return None, None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            return None, None
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            return None, None

    return None, None


def extract_citation(
    supabase: Any,
    source_id: str,
) -> dict[str, Any] | None:
    """Fetch source metadata (URL, title, AMC, scheme, last-updated) for a citation."""
    if supabase and hasattr(supabase, "table"):
        try:
            result = (
                supabase.table("fund_sources")
                .select("source_id, title, url, amc, scheme_name, last_updated")
                .eq("source_id", source_id)
                .maybe_single()
                .execute()
            )
            if result and result.data:
                return result.data
        except Exception:
            pass

    # Fallback to local sources.csv lookup
    try:
        csv_path = Path(__file__).resolve().parent.parent / "data" / "sources.csv"
        if not csv_path.exists():
            csv_path = Path(SOURCES_CSV)
        if csv_path.exists():
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("source_id") == source_id:
                        return {
                            "source_id": row["source_id"],
                            "title": row.get("title", ""),
                            "url": row.get("url", ""),
                            "amc": row.get("amc", ""),
                            "scheme_name": row.get("scheme_name", ""),
                            "last_updated": row.get("last_updated", ""),
                        }
    except Exception:
        pass

    return None


def run_rag(question: str) -> dict[str, Any]:
    """Full RAG pipeline using Google Gemini API and Supabase pgvector.

    1. Retrieves top chunks by embedding similarity.
    2. Builds indexed context [Source 1], [Source 2], etc.
    3. LLM generates grounded answer and returns supporting source index.
    4. Validates source index and selects the actual supporting chunk.
    5. Extracts citation metadata from the supporting chunk's source_id.

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
    supabase_client = _get_supabase_client()

    # If backend clients/keys are not configured, signal graceful lack of evidence
    if not GEMINI_API_KEY or not supabase_client:
        return {
            "answer": (
                "I could not find any factual information about this in the ingested sources. "
                "Please try asking about expense ratio, SIP, exit load, lock-in period, "
                "riskometer, or benchmark for any of the four HDFC schemes covered."
            ),
            "citation": None,
            "last_updated": None,
            "refused": False,
            "refusal_reason": None,
            "category": "FACTUAL",
        }

    # 1. Generate Gemini embedding
    embedding = generate_embedding(question)
    if not embedding:
        return {
            "answer": (
                "I could not generate a search embedding for your question. "
                "Please ensure the Gemini API key is configured and try again."
            ),
            "citation": None,
            "last_updated": None,
            "refused": False,
            "refusal_reason": None,
            "category": "FACTUAL",
        }

    # 2. Semantic search in Supabase
    chunks = semantic_search(supabase_client, embedding)
    if not chunks:
        return {
            "answer": "I could not find this information in the available sources.",
            "citation": None,
            "last_updated": None,
            "refused": True,
            "refusal_reason": "No matching context found in vector index",
            "category": "FACTUAL",
        }

    # 3. Filter by similarity — never answer without supporting evidence
    relevant = filter_by_similarity(chunks)
    if not relevant:
        return {
            "answer": "I could not find this information in the available sources.",
            "citation": None,
            "last_updated": None,
            "refused": True,
            "refusal_reason": "No retrieved context exceeded similarity threshold",
            "category": "FACTUAL",
        }

    # 4. Build indexed context with [Source 1], [Source 2], etc.
    context = build_context(relevant)
    max_sources = min(len(relevant), TOP_K)

    # 5. Generate grounded answer and extract supporting source index
    answer, supporting_idx = generate_answer(question, context, max_sources=max_sources)

    # 6. Validate the supporting source index and select the supporting chunk
    # If the LLM returned a valid index, use that chunk; otherwise fall back to top chunk
    if supporting_idx is not None and 1 <= supporting_idx <= len(relevant):
        supporting_chunk = relevant[supporting_idx - 1]
    else:
        supporting_chunk = relevant[0]

    # 7. Extract final citation metadata from the supporting chunk's source_id
    citation_data = extract_citation(supabase_client, supporting_chunk["source_id"])

    citation: dict[str, Any] | None = None
    last_updated: str | None = None

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

    # Fallback: use supporting chunk content directly if generation was empty
    if not answer:
        answer = supporting_chunk["content"][:500]

    # Check if the generated answer is an abstention/refusal
    refusal_phrases = [
        "could not find this information in the available sources",
        "could not find any factual information",
        "not found in the available sources",
        "cannot find this information",
    ]
    if any(p in answer.lower() for p in refusal_phrases):
        return {
            "answer": "I could not find this information in the available sources.",
            "citation": None,
            "last_updated": None,
            "refused": True,
            "refusal_reason": "Information not found in available sources",
            "category": "FACTUAL",
        }

    return {
        "answer": answer,
        "citation": citation,
        "last_updated": last_updated,
        "refused": False,
        "refusal_reason": None,
        "category": "FACTUAL",
    }
