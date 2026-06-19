# 🧠 Hybrid RAG Backend

Production-grade **Agentic Hybrid RAG** backend built with **FastAPI**, **LangGraph**, **Qdrant**, **MongoDB**, and **Redis**. It intelligently routes queries between your uploaded documents and the web, providing source-labeled, session-aware responses.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI entrypoint & health check
│   ├── __init__.py
│   │
│   ├── api/
│   │   └── routes.py           # REST endpoints (chat, documents, history)
│   │
│   ├── core/
│   │   ├── config.py           # Environment variables & logging setup
│   │   ├── database.py         # Async MongoDB (motor) & Redis clients
│   │   └── dependencies.py     # Shared dependency injection
│   │
│   ├── graph/
│   │   ├── state.py            # LangGraph state schema
│   │   ├── nodes.py            # Graph nodes (retrieve, generate, web search)
│   │   ├── edges.py            # Conditional routing logic
│   │   └── builder.py          # LangGraph workflow builder
│   │
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response models
│   │
│   ├── services/
│   │   ├── ingestion.py        # Document chunking & embedding pipeline
│   │   ├── vector_store.py     # Qdrant vector store operations
│   │   ├── cache.py            # Redis semantic caching
│   │   ├── chat.py             # Session-aware chat service
│   │   ├── database_mgr.py     # MongoDB document metadata manager
│   │   └── web_chain.py        # DuckDuckGo web search fallback chain
│   │
│   └── utils/
│       ├── file_processing.py  # PDF/DOCX text extraction
│       └── loaders.py          # File loader utilities
│
└── uploads/                    # Temporary file upload directory
```

---

## ⚙️ Prerequisites

| Dependency | Version  | Purpose                        |
|------------|----------|--------------------------------|
| Python     | ≥ 3.10   | Runtime                        |
| MongoDB    | ≥ 6.0    | Chat history & document metadata |
| Redis      | ≥ 7.0    | Semantic caching               |
| Groq API   | —        | LLM inference (Llama / Mixtral) |

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

Create a `.env` file in the **project root** (`RAG/.env`):

```env
GROQ_API_KEY=your_groq_api_key_here
REDIS_URL=redis://localhost:6379
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=hybrid_rag
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### 4. Start infrastructure services

```bash
# Start MongoDB
mongod --dbpath /data/db

# Start Redis
redis-server
```

### 5. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **`http://localhost:8000`**.

---

## 📡 API Endpoints

| Method   | Endpoint                        | Description                       |
|----------|---------------------------------|-----------------------------------|
| `GET`    | `/health`                       | Health check (Redis, Mongo, LLM)  |
| `POST`   | `/api/v1/documents/upload`      | Upload a PDF or DOCX document     |
| `GET`    | `/api/v1/documents`             | List all ingested documents       |
| `DELETE` | `/api/v1/documents/{doc_id}`    | Delete a document and its chunks  |
| `POST`   | `/api/v1/chat`                  | Send a query (returns sourced answer) |
| `GET`    | `/api/v1/chat/history/{session_id}` | Retrieve session chat history |
| `DELETE` | `/api/v1/chat/history/{session_id}` | Clear session chat history    |

### Example Chat Request

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is retrieval augmented generation?",
    "session_id": "your-session-uuid",
    "top_k": 5
  }'
```

### Example Response

```json
{
  "success": true,
  "answer": "Retrieval-Augmented Generation (RAG) is...",
  "source": "document",
  "cached": false,
  "retrieved_chunks": 5,
  "relevance_score": 0.87
}
```

---

## 🔄 Architecture Flow

```
User Query
    │
    ▼
┌──────────────┐     ┌──────────────────┐
│  Redis Cache  │────▶│  Return Cached   │
│  (hit?)       │     │  Response        │
└──────┬───────┘     └──────────────────┘
       │ miss
       ▼
┌──────────────┐
│  LangGraph   │
│  Router      │
└──────┬───────┘
       │
  ┌────┴────┐
  ▼         ▼
┌─────┐  ┌──────┐
│ Doc │  │ Web  │
│ RAG │  │Search│
└──┬──┘  └──┬───┘
   │        │
   ▼        ▼
┌──────────────┐
│  LLM (Groq)  │
│  Generation   │
└──────┬───────┘
       │
       ▼
  Cache + Return
```

---

## 🛠️ Tech Stack

- **FastAPI** — Async REST API framework
- **LangGraph** — Agentic workflow orchestration
- **LangChain** — Document processing & LLM chains
- **Groq** — Ultra-fast LLM inference
- **MongoDB (Motor)** — Async document/metadata storage
- **Redis** — Semantic response caching
- **Qdrant** — Vector similarity search
- **Sentence Transformers** — Embedding model (`all-MiniLM-L6-v2`)
- **DuckDuckGo Search** — Web fallback when no documents match
