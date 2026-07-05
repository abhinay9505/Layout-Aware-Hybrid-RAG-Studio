# 🧠 Layout-Aware Hybrid RAG Studio

RAG Studio is a production-grade, layout-aware **Agentic Hybrid RAG** platform. It specializes in parsing dense two-column academic papers (like the BERT paper), transcribing diagrams/flowcharts, and retrieving tabular data or exact statistics using a hybrid search engine (Vector + Fuzzy keyword matching) with Reciprocal Rank Fusion (RRF).

---

## 📁 Repository Structure

```
RAG/
├── backend/                  # FastAPI + LangGraph Backend
│   ├── app/                  # Application source code
│   ├── uploads/              # Uploaded document & figure storage
│   ├── Dockerfile            # Standalone Backend Dockerfile
│   ├── requirements.txt      # Python dependencies
│   └── README.md             # Backend setup & API reference
│
├── frontend/                 # Vanilla Web Client
│   ├── index.html            # Core layout & HTML structure
│   ├── style.css             # Premium dark-mode glassmorphic styling
│   ├── app.js                # Core controller & API integration
│   └── Dockerfile            # Standalone Frontend Dockerfile
│
├── faiss_index/              # Local FAISS vector store indexes
├── Dockerfile                # Unified multi-service Dockerfile
├── run.py                    # Multi-process CLI launcher
├── STRATEGY.md               # Pipeline architecture & QA framework
└── hybrid_rag.db             # Dual-mode SQLite fallback database
```

---

## ⚙️ Prerequisites

To run this platform locally, make sure you have:
1. **Python 3.10+** installed.
2. **Groq API Key** (configured in `.env`).
3. **Redis** (optional, fallback semantic caching will skip if unavailable).
4. **MongoDB** (optional, SQLite file fallback `hybrid_rag.db` will be used if MongoDB is offline).

---

## 🚀 Quick Start (Single-Command Run)

You can run both the frontend and backend simultaneously using the root `run.py` script:

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Configure environment keys
# Create a .env file in the root workspace directory with:
# GROQ_API_KEY=your_groq_api_key

# 4. Start full-stack services
python run.py
```

Once running, you can access the platform at:
- **Frontend Interface:** [http://localhost:5500](http://localhost:5500)
- **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Docker Deployment

The platform can be built and deployed in three different container layouts:

### A. Unified Single Container (Default)
Builds a single image that launches both the frontend and backend using `run.py`:

```bash
# Build the unified image
docker build -t rag-studio-fullstack .

# Run the unified container
docker run -d -p 8000:8000 -p 5500:5500 --env-file .env rag-studio-fullstack
```

### B. Separate Standalone Containers
You can build and deploy the services independently using their respective folder Dockerfiles:

#### 1. Backend Service
```bash
cd backend
docker build -t rag-backend .
docker run -d -p 8000:8000 --env-file ../.env rag-backend
```

#### 2. Frontend Service
```bash
cd frontend
docker build -t rag-frontend .
docker run -d -p 5500:80 rag-frontend
```

### C. Docker Compose Orchestration
Create a `docker-compose.yml` file in the root directory to manage the multi-container stack:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - backend_uploads:/app/uploads
      - backend_faiss:/app/faiss_index

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5500:80"
    depends_on:
      - backend

volumes:
  backend_uploads:
  backend_faiss:
```

---

## 💬 Core Features

1. **Layout-Aware PDF Parsing:** Uses Groq Multimodal vision processing (`llama-3.2-90b-vision-preview`) to parse academic papers following correct reading column orders.
2. **Visual Figure Extraction:** Automatically detects images, diagrams, and flowcharts (e.g. BERT input layers), transcribes them, and links them as context chunks.
3. **Hybrid Search Engine:** Combines semantic embedding similarity (via FAISS & HuggingFace sentences) with fuzzy keyword match queries (`rapidfuzz`) using Reciprocal Rank Fusion (RRF) to retrieve dense numbers/table grids.
4. **Interactive Inspector Panel:** An expandable JSON chunk source accordion in the chat bubble UI allowing full transparency of the retrieved context.
5. **Session Persistence:** Remembers chat histories across reloads and supports new session cleanup.
6. **Multi-Tenant User Authentication:** Secure signup, login, and logout framework powered by JWT bearer tokens, providing completely isolated workspace schemas, document libraries, and chat memories for every registered user.
