"""Configuration settings for the Facts-Only Mutual Fund RAG Chatbot."""

import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_KEY", ""))
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

SOURCES_CSV = os.getenv("SOURCES_CSV", "data/sources.csv")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.70"))
TOP_K = int(os.getenv("TOP_K", "4"))
