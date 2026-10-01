"""Ingestion runner script."""

import os
import sys

# Add parent directory to path so backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from ingestion import run_ingestion

if __name__ == "__main__":
    result = run_ingestion()
    print("Ingestion result:", result)
