# SmartRFP — AI Document Processing System (RAG + Live Pricing + Human-in-the-Loop)

An end-to-end, runnable implementation of the SmartRFP architecture and PRD:
upload an RFP → parse requirements → two agents run in parallel (RAG retrieval +
live pricing) → synthesize a draft with flags → a human approves/edits/rejects →
export to **DOCX / PDF / TXT**.

Built with **Streamlit + Groq + SQLite** (instead of OpenAI + PostgreSQL).

---

## 1. What you get

| Page | What it does |
|------|--------------|
| **Upload** | File upload (PDF/DOCX/TXT) + client details + **one "Generate Response" button** that runs the whole pipeline |
| **Dashboard** | Metric cards + a table of all RFPs, filterable by **reviewer role** (Junior / Senior / Supervisor / SME) and status; "Open" any row |
| **Review** | Full RFP details — draft sections, sources, **compliance / hallucination / missing-info flags**, requirements, pricing table, audit log — with **Approve / Edit inline / Send back / Reject** (the human gate) |
| **Export** | Appears after approval → **Download DOCX / PDF / TXT** (real files) |
| **Settings** | Groq status, knowledge base management, delete RFPs |

---

## 2. How to run (7 steps)

> ⚠️ **Keep the folder structure intact.** Always unzip the provided `smartrfp.zip`
> and run from the unzipped `smartrfp/` folder. Do **not** copy the `.py` files out
> into a single flat folder — `agents/` and `utils/` are Python packages, and
> flattening them causes `ModuleNotFoundError: No module named 'utils'`.

```bash
# 1. Go into the project folder (the one containing app.py)
cd smartrfp

# 2. (recommended) create a virtual environment
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (optional but recommended) add your Groq key
cp .env.example .env          # Windows: copy .env.example .env
#   then open .env and paste your key into GROQ_API_KEY=...

# 5. Launch the FastAPI server
uvicorn backend.main:app --reload

#6. Launch the app
streamlit run app.py

#7. Launch Prometheus Scraping:
(Download Prometheus ZIP, copy the files OTHER THAN the .yml into this following folder)
cd monitoring\prometheus
.\prometheus.exe --config.file=prometheus.yml
```

Streamlit App: http://localhost:8501
FastAPI Swagger Dashboard: http://127.0.0.1:8000/docs
Prometheus Metrics: http://localhost:8000/metrics
Grafana Dashboard: http://localhost:9090/

> **No Groq key?** The app still runs in **demo mode** — it produces deterministic,
> source-grounded drafts so you can see the full flow. Add a key any time for real
> LLM-written drafts; nothing else changes.

> Groq rotates models. The default is `openai/gpt-oss-20b`. If you get a
> "model not found" error, open `.env`, set `GROQ_MODEL` to a current model from
> https://console.groq.com/docs/models (e.g. `openai/gpt-oss-120b`).

---

## 3. Try it end-to-end (no UI) — proves the backend works

```bash
python test_pipeline.py
```

This creates a sample RFP, runs the pipeline, prints requirements / draft sections /
flags / pricing, and writes `exports/acme_test.{txt,docx,pdf}`.

---

## 4. Project structure

```
SmartRFP/

├── Dockerfile.backend  # Docker build instructions for FastAPI backend service
├── Dockerfile.frontend # Docker build instructions for Streamlit/UI frontend
├── Project_docs/       # Project documentation, design notes, architecture docs
├── README.md           # Project overview, setup instructions, usage guide

├── agents/             # LLM-based autonomous agents for different RFP tasks
│   ├── __init__.py     # Marks agents as Python package
│   ├── draft_generator.py  # Generates proposal/RFP draft sections using LLM
│   ├── extractor.py        # Extracts structured data from RFP documents
│   ├── pricing_agent.py    # Handles pricing estimation logic using AI
│   └── rag_agent.py        # Retrieval-Augmented Generation agent logic

├── app.py              # Entry point for UI or orchestration layer

├── backend/            # Core FastAPI backend (APIs + business logic)
│   ├── __init__.py
│   ├── config.py       # Backend configuration (env, settings, constants)
│   ├── crud.py         # Database CRUD operations (create/read/update/delete)
│   ├── database.py     # DB connection setup (SQLAlchemy engine/session)
│
│   ├── llm/            # LLM integration layer
│   │   ├── __init__.py
│   │   └── groq_client.py  # Groq LLM API client wrapper
│
│   ├── main.py         # FastAPI app initialization + middleware setup
│   ├── models.py       # SQLAlchemy ORM models (tables schema definitions)
│
│   ├── rag/            # Retrieval Augmented Generation pipeline
│   │   ├── __init__.py
│   │   ├── chunker.py      # Splits documents into chunks for embedding
│   │   ├── embedding.py    # Generates embeddings for text chunks
│   │   ├── ingestion.py    # Loads docs into vector DB pipeline
│   │   ├── pinecone_client.py # Pinecone vector DB integration
│   │   ├── prompt_builder.py  # Builds prompts for LLM queries
│   │   ├── retriever.py    # Retrieves relevant chunks from vector DB
│   │   ├── utils.py        # Helper functions for RAG pipeline
│   │   └── vector_store.py  # Abstraction over vector database
│
│   ├── routes/         # API endpoints (FastAPI routers)
│   │   ├── __init__.py
│   │   ├── dashboard.py    # Dashboard analytics endpoints
│   │   ├── export.py       # Export RFP results (PDF/Doc/etc.)
│   │   ├── health.py       # Health check endpoint for monitoring
│   │   ├── pricing.py      # Pricing-related API endpoints
│   │   ├── regenerate.py   # Regenerate RFP sections via LLM
│   │   ├── review.py       # Review/feedback endpoints
│   │   └── upload.py       # Upload RFP file endpoint (core entry)
│
│   ├── schemas.py      # Pydantic request/response schemas
│   ├── security.py     # Auth/security logic (if applicable)
│
│   ├── services/       # Business logic layer (orchestration)
│   │   ├── __init__.py
│   │   ├── estimation_service.py # Time/cost estimation logic
│   │   ├── pricing_service.py    # Pricing computation logic
│   │   └── rfp_service.py        # Core RFP processing pipeline
│
│   ├── services.py     # Legacy or combined service logic file
│
│   └── tools/          # External tool integrations
│       ├── calculator_tool.py  # Math/calculation helper tool
│       └── tavily_tool.py      # Web search tool (Tavily API)

├── config.py           # Global configuration (shared across modules)
├── database.py         # Shared DB utilities (possibly duplicate of backend one)
├── demo_seed.py        # Seed script for demo/sample database data
├── docker-compose.yml  # Multi-container setup (backend, frontend, monitoring)
├── evaluation.py       # Evaluation metrics for model/system performance

├── exports/            # Generated output files (reports, PDFs, etc.)

├── guardrails.py       # Safety, validation, and LLM output constraints
├── langsmith_utils.py  # LangSmith tracing/monitoring utilities
├── llm.py              # General LLM wrapper utilities (possibly legacy)

├── loadtest/           # Load testing scripts and reports (Locust)
│   ├── locust_upload.py # Upload endpoint stress test script
│   └── locustfile.py    # Main Locust load testing config

├── metrics.py          # Prometheus metrics definitions/exporters

├── monitoring/         # Observability stack configs
│   └── prometheus/
│       ├── Dockerfile  # Prometheus container setup
│       └── prometheus.yml # Prometheus scrape configuration

├── pipeline.py         # End-to-end RFP processing pipeline
├── pipeline_test.py    # Pipeline testing script
├── ragas_eval.py       # RAG evaluation using RAGAS framework

├── requirements.txt    # Python dependencies list

├── sampleRFPs/         # Sample RFP documents for testing/demo

├── seed_data.py        # Database initialization script
├── settings.py         # App-wide settings (env-based config loader)
├── state.py            # Global runtime state management (if used)

├── tests/              # Automated test suite
│   ├── conftest.py     # Pytest configuration and fixtures
│   ├── e2e/            # End-to-end tests (full workflow)
│   │   └── test_complete_workflow.py
│   ├── integration/    # Integration tests (modules together)
│   │   └── test_pipeline.py
│   └── unit/           # Unit tests (individual components)
│       ├── test_database.py
│       ├── test_extractor.py
│       ├── test_file_handler.py
│       ├── test_llm.py
│       ├── test_pricing.py
│       └── test_rag.py

├── ui/                 # Frontend/UI layer (Streamlit or internal UI system)
│   ├── api.py          # UI → backend API communication layer
│   ├── dashboard.py    # UI dashboard view
│   ├── export.py       # UI export controls
│   ├── help_pg.py      # Help/documentation page
│   ├── llm_eval.py     # UI for LLM evaluation metrics
│   ├── resource_cost.py # Cost estimation visualization
│   ├── review.py       # Review interface for RFP outputs
│   ├── settings.py     # UI settings page
│   ├── ui_utils.py     # UI helper functions
│   └── upload.py       # File upload interface

└── utils/              # Shared utility functions
    ├── __init__.py
    ├── exporter.py     # Export utilities (PDF/DOC generation)
    └── file_handler.py # File parsing and handling utilities
```

The SQLite file `smartrfp.db` is created automatically on first launch.

---

### Note on the "Vector DB"
Groq has no embeddings endpoint, and to keep the project **zero-setup** the RAG
agent uses **TF-IDF + cosine similarity** (scikit-learn) for relevance search.
It behaves the same way (retrieve the most relevant internal docs per requirement)
with no model downloads. To upgrade to true semantic embeddings, swap
`TfidfVectorizer` in `agents/rag_agent.py` for `sentence-transformers`
(`all-MiniLM-L6-v2`) — the function signature stays the same.

---

## 5. Safety behaviours from the PRD
- **Hallucination flag** — a draft claim (e.g. an SLA %) not found in any source is flagged.
- **Compliance flag** — compliance/data-residency content is flagged for SME confirmation.
- **Missing-info marker** — a requirement with no internal match is flagged, not faked.
- **Stale pricing** — pricing older than the current quarter is marked "STALE" and excluded from the total.
- **No export without approval** — the Export page blocks download until a human approves.
- **Audit trail** — every action (upload, parse, edit, approve, reject) is logged per RFP.

---

## 6. Troubleshooting
- **`ModuleNotFoundError: No module named 'utils'` (or `'agents'`)** → you're running
  from a folder where the `utils/` and `agents/` subfolders are missing or got
  flattened. Unzip `smartrfp.zip` fresh and run `streamlit run app.py` from inside
  the resulting `smartrfp/` folder so the package folders sit next to `app.py`.
- **`'source' is not recognized…` (Windows)** → use `venv\Scripts\activate`, not
  `source venv/bin/activate` (that's macOS/Linux syntax).
- **`streamlit: command not found`** → activate your venv, or run `python -m streamlit run app.py`.
- **Groq "model not found"** → update `GROQ_MODEL` in `.env` (see §2).
- **Legacy `.doc` upload fails** → convert to `.docx`, `.pdf`, or `.txt` first.
- **Want a clean slate** → delete `smartrfp.db` and restart.
```
