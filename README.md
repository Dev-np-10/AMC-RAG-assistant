# Facts-Only Mutual Fund RAG Chatbot

A retrieval-augmented generation (RAG) chatbot that answers **only factual questions** about mutual fund schemes from official AMC/SEBI/AMFI sources. It refuses investment advice, return predictions, comparisons, and blocks personal identifiable information (PII).

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  React + Vite +     │────▶│  Python / FastAPI     │────▶│  Supabase         │
│  Tailwind CSS UI    │◀────│  Backend              │◀────│  pgvector Store   │
└─────────────────────┘     │                       │     │  fund_sources    │
                            │  POST /api/chat        │     │  fund_chunks     │
                            │  POST /api/ingest      │     └──────────────────┘
                            │  GET  /api/sources     │           ▲
                            │  GET  /api/health      │           │
                            └──────────┬─────────────┘    ┌─────┴─────┐
                                       │                  │ Ingestion │
                                       ▼                  │ Pipeline  │
                                ┌──────────────┐          └──────────┘
                                │  OpenAI API  │
                                │  Embeddings  │
                                │  + GPT-4o    │
                                └──────────────┘
```

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, Tailwind CSS 3, Lucide icons |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small (1536-dim) |
| Vector Store | Supabase PostgreSQL + pgvector |
| Ingestion | Python pipeline (extraction → cleaning → chunking → embeddings → storage) |

## Coverage

- **AMC:** HDFC Mutual Fund
- **Schemes (4):**
  1. HDFC Balanced Advantage Fund
  2. HDFC Mid-Cap Opportunities Fund
  3. HDFC Short Term Debt Fund
  4. HDFC Index Fund - Nifty 50 Plan
- **Sources (24):** Factsheets, Scheme Information Documents, Key Information Memorandums, Portfolio Statements, Addendums, SEBI Circulars, AMFI Data

See [`data/sources.csv`](data/sources.csv) for the full list.

## Answer Policy

| Allowed | Refused |
|---------|---------|
| Expense ratio | Investment advice |
| SIP details (min amount) | Recommendations |
| Exit load | Return predictions |
| Lock-in period | Fund comparisons |
| Riskometer rating | Portfolio questions |
| Benchmark | PII (PAN, Aadhaar, OTP, phone, email, account) |
| Scheme statements | |

**Every factual response:**
- Maximum 3 sentences
- Exactly one official AMC/SEBI/AMFI citation
- "Last updated from sources: [date]"

## Query Classification

The `/api/chat` endpoint classifies every question into one of five categories before processing:

| Category | Behavior |
|----------|----------|
| `FACTUAL` | Run RAG pipeline: embed → semantic search → LLM → citation |
| `ADVICE` | Refuse — no retrieval, no LLM call |
| `PERFORMANCE` | Refuse — no retrieval, no LLM call |
| `PII` | Block immediately — no processing |
| `OUT_OF_SCOPE` | Refuse — suggest factual topics |

## API Endpoints

### POST /api/chat
Classify and answer a question.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the expense ratio of HDFC Balanced Advantage Fund?"}'
```

Response:
```json
{
  "answer": "The expense ratio of HDFC Balanced Advantage Fund is 1.50%...",
  "citation": {
    "source_id": "hdfc-balanced-factsheet",
    "title": "HDFC Balanced Advantage Fund - Factsheet",
    "url": "https://www.hdfcfund.com/...",
    "amc": "HDFC Mutual Fund",
    "scheme_name": "HDFC Balanced Advantage Fund",
    "last_updated": "2026-09-30"
  },
  "last_updated": "2026-09-30",
  "refused": false,
  "category": "FACTUAL"
}
```

### POST /api/ingest
Run the document ingestion pipeline (chunking → embeddings → pgvector storage).

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### GET /api/sources
List all ingested sources with metadata.

```bash
curl http://localhost:8000/api/sources
```

### GET /api/health
Health check — reports OpenAI and Supabase configuration status.

```bash
curl http://localhost:8000/api/health
```

## RAG Pipeline

```
User Question
    │
    ▼
┌──────────────┐
│  Classify    │──PII──▶ Block
│  (5-way)     │──ADVICE──▶ Refuse
└──────┬───────┘──PERFORMANCE──▶ Refuse
       │ FACTUAL
       ▼
┌──────────────┐
│  OpenAI      │
│  Embedding   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  pgvector    │
│  Top-k Search│──no evidence──▶ "Not found"
└──────┬───────┘
       │ chunks + metadata
       ▼
┌──────────────┐
│  Prompt      │
│  Construction│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  OpenAI LLM  │
│  Generation  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Citation    │
│  Extraction  │
└──────┬───────┘
       │
       ▼
  Final Response (≤3 sentences, 1 citation, last-updated date)
```

## Local Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- An OpenAI API key (optional — without it, the app runs in demo keyword-search mode)

### 1. Frontend

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Edit .env: set VITE_API_BASE to your backend URL (default: http://localhost:8000)

# Run dev server
npm run dev
```

The frontend runs on `http://localhost:5173`.

### 2. Backend

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Return to project root and set up environment
cd ..
cp .env.example .env
# Edit .env: set OPENAI_API_KEY and SUPABASE_* variables

# Start the FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend runs on `http://localhost:8000`.

API docs (Swagger UI) available at `http://localhost:8000/docs`.

### 3. Ingest Sources

To populate the pgvector store with real embeddings:

```bash
# Via API
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'

# Or via the ingestion script directly
cd backend
python -c "from ingestion import run_ingestion; print(run_ingestion())"
```

Without ingestion, the chatbot falls back to a built-in demo knowledge base with keyword matching.

## Project Structure

```
├── src/                            # Frontend
│   ├── App.tsx                    # Main chatbot UI
│   ├── types.ts                   # TypeScript interfaces
│   ├── components/
│   │   ├── ChatMessage.tsx        # Message bubble with citation
│   │   ├── ChatInput.tsx          # Question input
│   │   └── SourcePanel.tsx       # Collapsible source list
│   └── lib/
│       ├── api.ts                 # FastAPI client
│       ├── supabase.ts            # Supabase client
│       ├── guardrails.ts          # Client-side PII + advice blocking
│       └── demoKnowledge.ts      # Fallback knowledge base
├── backend/                        # Python FastAPI backend
│   ├── main.py                    # FastAPI app + 4 endpoints
│   ├── config.py                  # Environment config
│   ├── classifier.py              # 5-way query classifier
│   ├── rag.py                     # RAG pipeline
│   ├── ingestion.py               # Document ingestion pipeline
│   └── requirements.txt           # Python dependencies
├── supabase/
│   ├── config.toml                # Edge function config
│   ├── functions/
│   │   └── fund-rag/index.ts      # Edge function (legacy fallback)
│   └── migrations/
│       └── ...create_fund_rag_schema.sql  # pgvector schema
├── data/
│   ├── sources.csv               # 24 official sources
│   └── sample_qa.csv             # 31 evaluation Q&A pairs
├── tests/
│   └── eval.test.ts              # Evaluation tests
├── .env.example
└── README.md
```

## Evaluation

The evaluation suite tests three categories:

1. **Factual answers** — verifies correct source retrieval and key facts in the answer
2. **Advice refusal** — verifies investment advice questions are blocked
3. **PII blocking** — verifies questions containing PAN/Aadhaar/OTP are blocked

See [`data/sample_qa.csv`](data/sample_qa.csv) for the 31 test cases and [`tests/eval.test.ts`](tests/eval.test.ts) for the test implementation.

## Guardrails

### PII Detection
Blocks questions containing:
- PAN numbers (5 letters + 4 digits + 1 letter)
- Aadhaar numbers (12 digits)
- OTP codes (4-6 digits)
- Phone numbers (10 digits)
- Email addresses
- Account numbers

### Advice Detection
Blocks questions asking for:
- "Should I invest/buy/sell/redeem?"
- "Which fund should I choose?"
- "Is this a good investment?"
- "Will the NAV increase?"
- "Compare returns"
- "Recommend the best fund"
- "How much should I invest?"

### Performance Detection
Blocks questions about:
- Return predictions ("Will the NAV increase?")
- Performance comparisons ("Compare returns")
- Future performance ("Future returns?")
- CAGR / annualized returns

## Tech Stack

- **Frontend:** React 18, Vite 5, Tailwind CSS 3
- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Database:** PostgreSQL with pgvector extension
- **AI:** OpenAI GPT-4o-mini + text-embedding-3-small
- **Icons:** Lucide React

## License

This project is for educational/demo purposes. Mutual fund data is sourced from official public documents. Always consult a SEBI-registered financial advisor before investing.
