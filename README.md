# 🧠 Hybrid RAG Assistant

An intelligent **Retrieval-Augmented Generation** system that searches your uploaded documents first, then automatically falls back to the web when no relevant matches are found. Every response is source-labeled so you always know where the answer came from.

---

## 📁 Project Structure

```
RAG/
├── .env                  # Environment variables (API keys, DB URIs)
├── backend/              # FastAPI + LangGraph backend
│   └── app/
│       ├── main.py       # Server entrypoint
│       ├── api/          # REST routes
│       ├── core/         # Config, database clients, dependencies
│       ├── graph/        # LangGraph workflow (nodes, edges, state)
│       ├── models/       # Pydantic schemas
│       ├── services/     # Business logic (ingestion, cache, chat, vector store)
│       └── utils/        # File processing helpers
├── frontend/             # Vanilla JS chat UI
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── venv/                 # Python virtual environment
```

---

## ⚙️ Prerequisites

Make sure these are installed and running on your machine:

| Service    | Install Guide                                      | Default Port |
|------------|-----------------------------------------------------|-------------|
| **Python** ≥ 3.10 | [python.org](https://www.python.org/downloads/) | —           |
| **MongoDB** ≥ 6.0 | [mongodb.com](https://www.mongodb.com/try/download/community) | `27017` |
| **Redis** ≥ 7.0   | [redis.io](https://redis.io/download/)           | `6379`      |
| **Groq API Key**   | [console.groq.com](https://console.groq.com/)   | —           |

---

## 🚀 Installation & Setup

### Step 1 — Clone / Navigate to the project

```bash
cd RAG
```

### Step 2 — Create and activate a virtual environment

```bash
python -m venv venv
```

```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install Python dependencies

```bash
pip install fastapi uvicorn motor redis python-dotenv langchain langchain-groq langchain-community langgraph sentence-transformers qdrant-client python-multipart python-docx PyPDF2 duckduckgo-search pydantic aiohttp
```

### Step 4 — Configure environment variables

Edit the `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
REDIS_URL=redis://localhost:6379
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=hybrid_rag
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### Step 5 — Start infrastructure services

**MongoDB:**
```bash
mongod
```

**Redis:**
```bash
redis-server
```

> On Windows, you may need to run these as services or from their install directories.

---

## ▶️ Running the Application

### 1. Start the Backend

```bash
cd RAG
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running: open **http://localhost:8000/health** — you should see:
```json
{ "status": "healthy", "redis": true, "mongodb": true, "llm": true }
```

### 2. Start the Frontend

**Option A — Python HTTP server (recommended):**
```bash
cd frontend
python -m http.server 5500
```

**Option B — Node.js:**
```bash
npx -y serve ./frontend -l 5500
```

**Option C — VS Code Live Server:**
Right-click `frontend/index.html` → **Open with Live Server**

### 3. Open the App

Navigate to **http://localhost:5500** in your browser.

---

## 🎯 Quick Start Guide

1. **Upload a document** — Drag a PDF or DOCX into the sidebar upload area
2. **Ask a question** — Type your query in the chat input and press Enter
3. **Check the source** — Look at the badge on each response:
   - `📄 Document` — Answer came from your uploaded files
   - `🌐 Web Search` — No match in docs, answer came from the web
   - `⚡ Cached` — Response was served from Redis cache

---

## 📡 API Reference

| Method   | Endpoint                            | Description                     |
|----------|-------------------------------------|---------------------------------|
| `GET`    | `/health`                           | Health check                    |
| `POST`   | `/api/v1/documents/upload`         | Upload PDF/DOCX                 |
| `GET`    | `/api/v1/documents`                 | List documents                  |
| `DELETE` | `/api/v1/documents/{doc_id}`        | Delete a document               |
| `POST`   | `/api/v1/chat`                     | Send a chat query               |
| `GET`    | `/api/v1/chat/history/{session_id}` | Get session history             |
| `DELETE` | `/api/v1/chat/history/{session_id}` | Clear session history           |

---

## 🛠️ Tech Stack

| Layer      | Technology                                         |
|------------|-----------------------------------------------------|
| **API**    | FastAPI, Uvicorn                                    |
| **AI/LLM** | Groq (Llama/Mixtral), LangChain, LangGraph         |
| **Search** | Qdrant (vector), DuckDuckGo (web fallback)          |
| **Storage**| MongoDB (metadata/history), Redis (cache)           |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`)     |
| **Frontend** | Vanilla HTML/CSS/JS, Glassmorphism dark theme     |

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ConnectionRefusedError` on Redis | Make sure `redis-server` is running on the configured port |
| `ConnectionRefusedError` on MongoDB | Make sure `mongod` is running |
| CORS errors in browser | Backend includes CORS middleware — ensure it's running on port `8000` |
| `Cannot connect to server` in chat | Start the backend first, then the frontend |
| Slow first query | The embedding model downloads on first use (~90MB) |
