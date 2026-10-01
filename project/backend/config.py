"""Configuration — loads secrets from environment variables."""

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIM = 1536
OPENAI_LLM_MODEL = "gpt-4o-mini"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

SOURCES_CSV = os.getenv("SOURCES_CSV", "data/sources.csv")

SIMILARITY_THRESHOLD = 0.70
TOP_K = 5
MAX_ANSWER_SENTENCES = 3
