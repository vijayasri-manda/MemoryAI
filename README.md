# 🧠 AI Memory Assistant

> **Production-ready AI chat application with RAG-based persistent memory** — your AI remembers everything across sessions.

[![CI/CD](https://github.com/your-org/ai-memory-assistant/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/ai-memory-assistant/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://reactjs.org)

---

## ✨ What It Does

Current LLMs forget everything when a chat ends. This solves that.

**AI Memory Assistant** stores every conversation as semantic embeddings in a vector database. Before each response, it retrieves the most relevant past memories and injects them into the prompt — making the AI behave as though it genuinely remembers you.

---

## 🏗️ Architecture

```
React (Vite + TailwindCSS + Framer Motion)
           ↕ SSE Streaming / REST
FastAPI (Auth, Chat, Memory, RAG Pipeline)
    ↕               ↕               ↕
PostgreSQL      ChromaDB/FAISS    OpenAI/Anthropic/Ollama
(Users, Msgs)   (Embeddings)      (LLM)
```

### RAG Pipeline
```
User Query → Embed → Vector Search → Re-rank → Deduplicate
→ Compress → Inject into Prompt → Stream LLM Response
→ Extract Memories → Store Embeddings (async background)
```

---

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
git clone https://github.com/your-org/ai-memory-assistant
cd ai-memory-assistant

# Configure your API keys
cp backend/.env.example backend/.env
# Edit backend/.env → set GEMINI_API_KEY, SECRET_KEY

# Start everything
docker compose up -d

# Run database migrations
docker compose exec backend alembic upgrade head

# Open the app
open http://localhost:5173
```

### Local Development

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env  # edit with your keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev  # → http://localhost:5173
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite 8, TailwindCSS, Framer Motion |
| **State** | Zustand + React Query |
| **Backend** | FastAPI, Python 3.12, LangChain, SQLAlchemy 2 |
| **Auth** | JWT (access + refresh tokens), bcrypt |
| **Database** | PostgreSQL 16 with asyncpg / SQLite |
| **Vector DB** | ChromaDB / FAISS / Pinecone / Weaviate (configurable) |
| **Embeddings** | Sentence Transformers / Gemini / OpenAI / Instructor XL |
| **LLM** | Gemini 2.5 Flash, Gemini 1.5 Pro, GPT-4o, Claude 3.5, Llama 3 (Ollama) |
| **Infra** | Docker, Docker Compose, Kubernetes, Nginx, Redis |
| **CI/CD** | GitHub Actions |

---

## 🗂️ Project Structure

```
ai-memory-assistant/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API routes (auth, chat, memory, health)
│   │   ├── core/            # Config, DB, security, logging
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic (auth, chat, memory, LLM, embedding, extraction)
│   │   ├── rag/             # RAG pipeline (chunker, retriever, reranker, compressor)
│   │   └── vector_store/    # ChromaDB, FAISS, Pinecone adapters
│   ├── alembic/             # Database migrations
│   ├── tests/               # Unit, integration, RAG evaluation
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # Sidebar, MessageBubble, ChatInput, MemoryPanel
│   │   ├── pages/           # ChatPage, MemoryPage, SettingsPage, Auth
│   │   ├── lib/             # API client, utilities, services
│   │   ├── store/           # Zustand state (auth, UI)
│   │   └── types/           # TypeScript types
│   └── Dockerfile
├── docker/
│   ├── nginx/               # Nginx reverse proxy config
│   └── postgres/            # DB init script
├── k8s/
│   ├── deployments/         # K8s Deployments + PVCs
│   ├── services/            # Services + Ingress + HPA
│   └── configmaps/          # ConfigMap + Secrets
├── docs/
│   └── DOCUMENTATION.md     # SRS, HLD, LLD, API docs, Testing
├── .github/workflows/       # CI/CD pipelines
└── docker-compose.yml
```

---

## 🧠 Memory System

The memory system intelligently stores and retrieves:

| Stored ✅ | Ignored ❌ |
|-----------|----------|
| Project details | "Hello", "Thanks" |
| Coding preferences | Small talk |
| Goals and plans | Duplicate info |
| Technical decisions | Expired memories |
| Education/skills | Low-importance content |

Memory metadata includes: `importance_score`, `tags`, `timestamp`, `session_id`, `access_count`, `expires_at`.

---

## 🔧 Configuration

Key settings in `backend/.env`:

```env
# LLM
LLM_PROVIDER=google           # google | openai | anthropic | ollama
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=AIzaSy...

# Vector Store
VECTOR_STORE_TYPE=chroma      # chroma | faiss | pinecone | weaviate

# Embeddings
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2

# RAG Tuning
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.65
RAG_RERANK_ENABLED=true
```

---

## 🧪 Testing

```bash
cd backend

# Unit tests
pytest tests/unit/ -v --cov=app

# Integration tests
pytest tests/integration/ -v

# RAG evaluation (retrieval precision & recall)
python tests/rag/evaluate_retrieval.py
```

---

## 🚢 Production Deployment

See [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md#deployment) for:
- Kubernetes deployment with HPA
- SSL/TLS with cert-manager
- Monitoring with Prometheus
- Database backup strategies
- Production security checklist

---

## 📄 License

MIT © 2024 Your Organization

---

> Built with ❤️ using FastAPI, React, ChromaDB, and LangChain