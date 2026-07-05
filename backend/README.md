# 🧠 Hybrid RAG Backend

Production-grade **Agentic Hybrid RAG** backend built with **FastAPI**, **LangGraph**, **FAISS**, **MongoDB/SQLite**, and **Redis/In-Memory Cache**. It intelligently routes queries between your uploaded documents and the web, providing source-labeled, session-aware responses.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI entrypoint & health check
│   ├── __init__.py
│   │
│   ├── api/
│   │   └── routes.py           # REST endpoints with OpenAPI tags (chat, documents, history)
│   │
│   ├── core/
│   │   ├── config.py           # Environment variables & logging setup
│   │   ├── database.py         # Dual-mode SQLite/MongoDB & Redis/In-Memory clients
│   │   └── dependencies.py     # Shared dependency injection
│   │
│   ├── graph/
│   │   ├── state.py            # LangGraph state schema
│   │   ├── nodes.py            # Graph nodes (restored hybrid search, query expansion, generation)
│   │   ├── edges.py            # Conditional routing logic
│   │   └── builder.py          # LangGraph workflow builder
│   │
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response models
│   │
│   ├── services/
│   │   ├── ingestion.py        # Document chunking & embedding pipeline
│   │   ├── vector_store.py     # Local FAISS vector store operations
│   │   ├── cache.py            # Dual-mode Redis/Local semantic caching
│   │   ├── chat.py             # Session-aware chat service
│   │   ├── database_mgr.py     # Document metadata manager
│   │   └── web_chain.py        # DuckDuckGo web search fallback chain
│   │
│   └── utils/
│       ├── file_processing.py  # PDF/DOCX text extraction
│       └── loaders.py          # File loader utilities
│
└── uploads/                    # Temporary file upload directory
```

---

## ⚙️ Prerequisites & Database Modes

The backend runs in **Dual-Mode** to enable zero-configuration local runs while remaining ready for production MongoDB and Redis:

| Dependency | Required | Fallback Option | Purpose |
|---|---|---|---|
| **Python** | Yes (≥ 3.10) | — | Runtime |
| **MongoDB** | Optional | **SQLite** (`hybrid_rag.db`) | Chat history & document metadata |
| **Redis** | Optional | **Local Memory Cache** | Semantic caching |
| **FAISS** | Yes (Local) | — | Vector similarity search index |
| **Groq API** | Yes | — | LLM inference (Llama / Mixtral) |

---

## 🚀 Getting Started

### 1. Create & activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the **project root** or **backend/app/.env**:

```env
GROQ_API_KEY=your_groq_api_key_here
REDIS_URL=redis://localhost:6379
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=hybrid_rag
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### 4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **`http://localhost:8000`**.

---

## 📡 API Endpoints

All REST routes are tagged for clean OpenAPI documentation.

### Authentication (`tags=["Authentication"]`)
* `POST` `/api/v1/auth/signup` — Register a new user
* `POST` `/api/v1/auth/login` — Authenticate and retrieve JWT token
* `GET` `/api/v1/auth/me` — Retrieve active user context

### Documents (`tags=["Documents"]`)
* `POST` `/api/v1/documents/upload` — Upload a PDF or DOCX document
* `GET` `/api/v1/documents` — List metadata of uploaded documents
* `DELETE` `/api/v1/documents/{doc_id}` — Delete document chunks and metadata

### Chat & History (`tags=["Chat"]`)
* `POST` `/api/v1/chat` — Query RAG pipeline (returns source-labeled response)
* `GET` `/api/v1/chat/history/{session_id}` — Retrieve chat session messages
* `DELETE` `/api/v1/chat/history/{session_id}` — Clear chat session history

---

## 🔄 Architecture Flow

```
User Query
    │
    ▼
┌──────────────┐     ┌──────────────────┐
│  Redis/Local │────▶│  Return Cached   │
│  Cache Hit?  │     │  Return Cached   │
│  (Semantic)  │     │  Response        │
└──────┬───────┘     └──────────────────┘
       │ miss
       ▼
┌──────────────────────────────────────┐
│        LangGraph RAG Pipeline        │
│ 1. Normalize/Expand Query            │
│ 2. Hybrid Retrieve (BM25 + Vector)   │
│ 3. Specific Chunks Priority Injection│
│ 4. Reciprocal Rank Fusion & Rerank   │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│         LLM (Groq) Generator         │
│  - Formats tables if comparison      │
│  - Strict no-evidence checks         │
└──────────────────┬───────────────────┘
                   │
                   ▼
            Cache + Return
```
