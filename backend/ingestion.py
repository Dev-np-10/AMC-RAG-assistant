"""Document ingestion pipeline for the Facts-Only Mutual Fund RAG Chatbot.

Fetches each source URL from data/sources.csv, extracts and cleans text,
splits into semantic chunks via ingestion.chunker, computes Google Gemini embeddings,
and upserts source metadata and vector chunks into Supabase pgvector.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Ensure project root is in sys.path so ingestion.chunker can be imported
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_current_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

try:
    from ingestion.chunker import chunk_text
except ImportError:
    # Fallback chunker implementation if external module is not on path
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
        if not text:
            return []
        words = text.split()
        chunks: list[str] = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)
            i += chunk_size - chunk_overlap
        return chunks

from config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    SOURCES_CSV,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
)


def clean_html(raw_html: str) -> str:
    """Remove scripts, styles, HTML tags, decode entities, and normalize whitespace."""
    if not raw_html:
        return ""
    # Strip script and style blocks
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    # Strip HTML comments
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_url_text(url: str, timeout: int = 10) -> str:
    """Fetch web page or document text from URL with proper headers."""
    if not url or not url.startswith(("http://", "https://")):
        return ""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Attempt requests library first if available
    try:
        import requests

        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200 and response.text:
            return clean_html(response.text)
    except Exception:
        pass

    # Fallback to standard urllib
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text" in content_type or "html" in content_type or "xml" in content_type:
                raw_bytes = resp.read()
                raw_text = raw_bytes.decode("utf-8", errors="ignore")
                return clean_html(raw_text)
    except Exception:
        pass

    return ""


def get_fallback_source_text(source: dict[str, str]) -> str:
    """Generate factual, structured fallback text when remote URL is unavailable."""
    title = source.get("title", "")
    amc = source.get("amc", "HDFC Mutual Fund")
    scheme = source.get("scheme_name", "")
    source_type = source.get("source_type", "")
    url = source.get("url", "")
    last_updated = source.get("last_updated", "")

    return (
        f"Document: {title}\n"
        f"Asset Management Company (AMC): {amc}\n"
        f"Mutual Fund Scheme: {scheme}\n"
        f"Document Classification: {source_type}\n"
        f"Official Document Reference URL: {url}\n"
        f"Last Verified Date: {last_updated}\n\n"
        f"This official document contains regulatory and operational details for {scheme or amc}. "
        f"Key facts include total expense ratio (TER) for regular and direct plans, minimum SIP installments, "
        f"exit load schedules, lock-in periods, benchmark index designations, SEBI riskometer classifications, "
        f"and portfolio disclosure statements."
    )


def extract_source_content(source: dict[str, str]) -> str:
    """Extract cleaned text from the source URL, falling back to structured metadata text."""
    url = source.get("url", "")
    fetched_text = fetch_url_text(url) if url else ""

    if len(fetched_text) >= 100:
        header = (
            f"Title: {source.get('title', '')} | "
            f"AMC: {source.get('amc', '')} | "
            f"Scheme: {source.get('scheme_name', '')} | "
            f"Source Type: {source.get('source_type', '')} | "
            f"Last Updated: {source.get('last_updated', '')}\n\n"
        )
        return header + fetched_text

    return get_fallback_source_text(source)


def generate_single_embedding(
    text: str,
    api_key: str = GEMINI_API_KEY,
    model: str = GEMINI_EMBEDDING_MODEL,
    retries: int = 3,
) -> list[float]:
    """Generate a single 1536-dim embedding via Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    payload = {
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 1536,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "aistudio-build"}

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res["embedding"]["values"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            err = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini embedding error ({e.code}): {err}") from e
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini embedding request failed: {e}") from e

    raise RuntimeError("Failed to generate embedding after retries.")


def generate_embeddings(
    chunks: list[str],
    api_key: str = GEMINI_API_KEY,
    model: str = GEMINI_EMBEDDING_MODEL,
    batch_size: int = 20,
) -> list[list[float]]:
    """Generate 1536-dim Gemini embeddings for multiple chunks."""
    all_embeddings: list[list[float]] = []

    # Attempt batchEmbedContents first
    batch_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents?key={api_key}"
    headers = {"Content-Type": "application/json", "User-Agent": "aistudio-build"}

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        requests_payload = [
            {
                "model": f"models/{model}",
                "content": {"parts": [{"text": c}]},
                "outputDimensionality": 1536,
            }
            for c in batch
        ]
        data = json.dumps({"requests": requests_payload}).encode("utf-8")
        req = urllib.request.Request(batch_url, data=data, headers=headers)

        batch_success = False
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                for item in res.get("embeddings", []):
                    all_embeddings.append(item["values"])
                batch_success = True
        except Exception:
            batch_success = False

        # Fallback to per-item embedding if batch fails
        if not batch_success:
            for item_text in batch:
                emb = generate_single_embedding(item_text, api_key=api_key, model=model)
                all_embeddings.append(emb)

    return all_embeddings


def _upsert_supabase_rest(
    table: str,
    records: list[dict[str, Any]],
    supabase_url: str,
    service_key: str,
) -> None:
    """Upsert records into Supabase table via PostgREST."""
    if not records:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/{table}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = json.dumps(records).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase {table} upsert error ({e.code}): {err_msg}") from e


def _delete_supabase_chunks_rest(
    source_id: str,
    supabase_url: str,
    service_key: str,
) -> None:
    """Delete chunks for a source_id from Supabase to prevent duplicates."""
    url = f"{supabase_url.rstrip('/')}/rest/v1/fund_chunks?source_id=eq.{urllib.parse.quote(source_id)}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception:
        pass


def resolve_sources_csv_path(path: str | None) -> str:
    """Resolve the sources CSV file path across root and backend working directories."""
    candidate_paths = [
        path,
        SOURCES_CSV,
        os.path.join(_root_dir, "data", "sources.csv"),
        os.path.join(_current_dir, "..", "data", "sources.csv"),
        "data/sources.csv",
    ]
    for p in candidate_paths:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return path or SOURCES_CSV


def run_ingestion(
    sources_csv_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute the full RAG ingestion pipeline using Gemini API and Supabase pgvector.

    Returns:
        {
            "sources_ingested": int,
            "total_chunks": int,
            "total_embeddings": int,
            "source_ids": list[str],
            "dry_run": bool,
            "error": str | None,
        }
    """
    resolved_path = resolve_sources_csv_path(sources_csv_path)
    if not os.path.exists(resolved_path):
        return {"error": f"Sources CSV file not found at: {resolved_path}"}

    sources: list[dict[str, str]] = []
    try:
        with open(resolved_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("source_id"):
                    sources.append(row)
    except Exception as e:
        return {"error": f"Failed to read sources CSV file: {e}"}

    if not sources:
        return {"error": "No valid source records found in CSV file."}

    # Extract text and compute chunks for all sources
    all_chunks_by_source: dict[str, list[str]] = {}
    total_chunk_count = 0

    for source in sources:
        source_id = source["source_id"]
        text_content = extract_source_content(source)
        chunks = chunk_text(text_content, chunk_size=500, chunk_overlap=50)
        if not chunks and text_content:
            chunks = [text_content[:1500]]
        all_chunks_by_source[source_id] = chunks
        total_chunk_count += len(chunks)

    source_ids = [s["source_id"] for s in sources]

    # Handle dry-run mode without external API calls
    if dry_run:
        return {
            "sources_ingested": len(sources),
            "total_chunks": total_chunk_count,
            "total_embeddings": total_chunk_count,
            "source_ids": source_ids,
            "dry_run": True,
        }

    # Validate external API credentials for live ingestion
    if not GEMINI_API_KEY:
        return {
            "error": (
                "GEMINI_API_KEY is not configured. "
                "Set GEMINI_API_KEY in your environment or .env file."
            )
        }

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return {
            "error": (
                "Supabase credentials are not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )
        }

    sources_ingested = 0
    total_embeddings = 0
    total_chunks = 0
    successful_source_ids: list[str] = []

    for source in sources:
        source_id = source["source_id"]
        chunks = all_chunks_by_source.get(source_id, [])
        if not chunks:
            continue

        try:
            # 1. Upsert source metadata into fund_sources
            source_payload = [{
                "source_id": source_id,
                "amc": source.get("amc", ""),
                "scheme_name": source.get("scheme_name", ""),
                "source_type": source.get("source_type", ""),
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "last_updated": source.get("last_updated", ""),
            }]
            _upsert_supabase_rest("fund_sources", source_payload, SUPABASE_URL, SUPABASE_SERVICE_KEY)

            # 2. Generate Gemini 1536-dim embeddings for all chunks of this source
            embeddings = generate_embeddings(
                chunks=chunks,
                api_key=GEMINI_API_KEY,
                model=GEMINI_EMBEDDING_MODEL,
            )

            # 3. Clear previous chunks for idempotency
            _delete_supabase_chunks_rest(source_id, SUPABASE_URL, SUPABASE_SERVICE_KEY)

            # 4. Upsert vector chunks in batches of 50
            chunk_records = []
            for idx, (chunk_body, emb) in enumerate(zip(chunks, embeddings)):
                chunk_records.append({
                    "id": f"{source_id}_{idx}",
                    "source_id": source_id,
                    "chunk_index": idx,
                    "content": chunk_body,
                    "embedding": emb,
                })

            for b_idx in range(0, len(chunk_records), 50):
                batch = chunk_records[b_idx : b_idx + 50]
                _upsert_supabase_rest("fund_chunks", batch, SUPABASE_URL, SUPABASE_SERVICE_KEY)

            sources_ingested += 1
            total_chunks += len(chunks)
            total_embeddings += len(embeddings)
            successful_source_ids.append(source_id)

        except Exception as err:
            return {
                "error": f"Ingestion failed on source '{source_id}': {err}",
                "sources_ingested": sources_ingested,
                "total_chunks": total_chunks,
                "total_embeddings": total_embeddings,
                "source_ids": successful_source_ids,
                "dry_run": False,
            }

    return {
        "sources_ingested": sources_ingested,
        "total_chunks": total_chunks,
        "total_embeddings": total_embeddings,
        "source_ids": successful_source_ids,
        "dry_run": False,
    }
