# AI Memory Assistant — Complete Documentation

## Table of Contents
- [Architecture Overview](#architecture)
- [SRS](#srs)
- [HLD](#hld)
- [LLD](#lld)
- [API Reference](#api)
- [Deployment Guide](#deployment)
- [User Manual](#user-manual)
- [Testing Strategy](#testing)

---

## Architecture Overview {#architecture}

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                   │
│  React + TypeScript + Vite  │  TailwindCSS + Framer Motion              │
│  React Query + Zustand       │  Streaming SSE + Markdown                 │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTPS / SSE
┌────────────────────────────────▼────────────────────────────────────────┐
│                         NGINX GATEWAY                                   │
│  Rate limiting │ SSL termination │ Reverse proxy │ Gzip                 │
└──────┬──────────────────────────┬──────────────────────────────────────┘
       │ /api/*                   │ /*
┌──────▼──────────┐     ┌─────────▼──────────┐
│  FastAPI Backend │     │   React Frontend   │
│  (2+ replicas)  │     │    (Nginx SPA)      │
└──────┬───┬──────┘     └────────────────────┘
       │   │
       │   ├── PostgreSQL (Users, Conversations, Messages, Memory metadata)
       │   ├── Redis (Caching, Rate limiting)
       │   └── ChromaDB/FAISS/Pinecone (Vector embeddings)
       │
       └── External LLM APIs (OpenAI / Anthropic / Google / Ollama)
```

### Service Layer Architecture
```
Request Flow:
  User Query
      ↓
  [Auth Service]  — JWT validation
      ↓
  [Chat Service]  — orchestrates the full pipeline
      ↓
  [Embedding Service]  — embeds the query
      ↓
  [Retrieval Service]  — semantic search in vector DB
      ↓
  [Re-ranker]          — cross-encoder re-ranking
      ↓
  [Deduplicator]       — remove duplicate memories
      ↓
  [Context Compressor] — fit within token budget
      ↓
  [Prompt Builder]     — inject memories into system prompt
      ↓
  [LLM Service]        — stream from GPT/Claude/Gemini/Ollama
      ↓
  [Memory Service]     — async: extract, score, store new memories
      ↓
  Response streamed to user
```

---

## Software Requirements Specification (SRS) {#srs}

### 1. Introduction
**Product:** AI Memory Assistant  
**Version:** 1.0.0  
**Purpose:** A production-ready AI chat application that overcomes the stateless limitation of LLMs by implementing a RAG-based persistent memory system.

### 2. Functional Requirements

#### 2.1 Authentication
| ID | Requirement |
|----|-------------|
| AUTH-01 | Users shall register with username, email, password |
| AUTH-02 | System shall authenticate via JWT (access + refresh tokens) |
| AUTH-03 | Tokens shall expire (access: 24h, refresh: 30d) |
| AUTH-04 | Each user shall have isolated memory space |

#### 2.2 Chat
| ID | Requirement |
|----|-------------|
| CHAT-01 | UI shall support real-time streaming responses |
| CHAT-02 | Messages shall support Markdown and code highlighting |
| CHAT-03 | Users shall be able to copy, regenerate, and edit messages |
| CHAT-04 | Conversation history shall be paginated |

#### 2.3 Memory System
| ID | Requirement |
|----|-------------|
| MEM-01 | Every conversation shall be chunked and embedded |
| MEM-02 | Embeddings shall be stored with user_id, session_id, timestamp, tags, importance |
| MEM-03 | Top-K memories shall be retrieved via semantic similarity before each LLM call |
| MEM-04 | System shall deduplicate memories (cosine threshold: 0.92) |
| MEM-05 | Memories shall have configurable TTL (default: 365 days) |
| MEM-06 | System shall extract importance score (0–1) for each memory chunk |
| MEM-07 | System shall ignore greetings, small talk, and short messages (<20 tokens) |

#### 2.4 RAG Pipeline
| ID | Requirement |
|----|-------------|
| RAG-01 | Query shall be embedded and used for semantic search |
| RAG-02 | System shall retrieve Top-K memories (configurable, default: 5) |
| RAG-03 | Retrieved memories shall be re-ranked using cross-encoder scores |
| RAG-04 | Context shall be compressed if exceeds token budget |
| RAG-05 | Retrieved memories shall be injected into system prompt |

### 3. Non-Functional Requirements
| Category | Requirement |
|----------|-------------|
| Performance | API response < 200ms (excl. LLM streaming) |
| Scalability | Backend horizontally scalable (K8s HPA) |
| Security | JWT auth, HTTPS only, rate limiting, input validation |
| Reliability | 99.9% uptime target, health checks, graceful restart |
| Maintainability | SOLID principles, type hints, docstrings, tests |

---

## High-Level Design (HLD) {#hld}

### Component Diagram
```
┌─────────────────── Backend (FastAPI) ────────────────────┐
│                                                           │
│  API Layer          Services              Infrastructure  │
│  ─────────          ────────              ──────────────  │
│  auth.py    →→→     AuthService    →→→    PostgreSQL      │
│  chat.py    →→→     ChatService    →→→    Redis           │
│  memory.py  →→→     MemoryService  →→→    ChromaDB        │
│  health.py          EmbedService   →→→    FAISS           │
│                     LLMService     →→→    Google Gemini API │
│                                                           │
│  RAG Pipeline                                             │
│  ────────────                                             │
│  chunker → embedder → vector_store → reranker             │
│  → deduplicator → compressor → prompt_builder → LLM      │
└───────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Ingest:** User message → Chunker → Embedding → Vector Store + PostgreSQL
2. **Retrieve:** Query embedding → Vector search → Re-rank → Deduplicate → Compress
3. **Generate:** System prompt + memories + chat history → LLM → Stream response
4. **Store:** LLM response → Memory extraction → Importance scoring → Vector Store

---

## Low-Level Design (LLD) {#lld}

### Database Schema

```sql
-- Users
users (
  id UUID PK,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Conversations
conversations (
  id UUID PK,
  user_id UUID FK → users(id),
  title VARCHAR(500),
  summary TEXT,
  is_archived BOOLEAN DEFAULT false,
  message_count INT DEFAULT 0,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Messages
messages (
  id UUID PK,
  conversation_id UUID FK → conversations(id),
  role VARCHAR(20) CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  tokens_used INT,
  model VARCHAR(100),
  metadata JSONB,
  created_at TIMESTAMPTZ
)

-- Memory Chunks (vector metadata)
memory_chunks (
  id UUID PK,
  user_id UUID FK → users(id),
  source_conversation_id UUID FK → conversations(id),
  source_message_id UUID FK → messages(id),
  content TEXT NOT NULL,
  summary TEXT,
  chunk_index INT DEFAULT 0,
  importance_score FLOAT DEFAULT 0.5,
  tags TEXT[] DEFAULT '{}',
  embedding_model VARCHAR(100),
  vector_id VARCHAR(255),  -- ID in vector store
  access_count INT DEFAULT 0,
  last_accessed TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Memory Summaries (per conversation)
memory_summaries (
  id UUID PK,
  conversation_id UUID FK → conversations(id),
  user_id UUID FK → users(id),
  summary TEXT NOT NULL,
  key_points TEXT[],
  created_at TIMESTAMPTZ
)
```

### Vector Store Schema (ChromaDB / FAISS / Pinecone)
```
Collection: ai_memory_embeddings_{user_id}
Document:   memory chunk text
Embedding:  float[384 | 1024 | 1536]  (model-dependent)
Metadata: {
  user_id, session_id, chunk_id (UUID),
  timestamp, tags[], importance_score,
  source: 'conversation' | 'summary',
}
```

### RAG Pipeline (Step-by-Step)
```python
async def rag_pipeline(query, user_id, session_id):
    # 1. Embed query
    q_vec = await embed(query)

    # 2. Semantic search
    candidates = await vector_store.search(q_vec, top_k=20, filter={user_id})

    # 3. Re-rank with cross-encoder
    ranked = reranker.rank(query, candidates)[:10]

    # 4. Deduplicate (cosine sim > 0.92)
    unique = deduplicator.filter(ranked)

    # 5. Score threshold filter (> 0.65)
    filtered = [m for m in unique if m.score > 0.65][:5]

    # 6. Compress to token budget (2000 tokens)
    compressed = compressor.compress(filtered, max_tokens=2000)

    # 7. Build system prompt
    prompt = prompt_builder.build(compressed, session_history)

    # 8. Stream LLM response
    async for chunk in llm.stream(prompt + query):
        yield chunk

    # 9. Store new memories (background task)
    asyncio.create_task(memory_service.ingest(response, user_id, session_id))
```

---

## API Reference {#api}

### Authentication

#### POST /api/v1/auth/register
```json
Request: {
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword",
  "full_name": "John Doe"
}
Response 201: {
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "uuid", "username": "johndoe", "email": "..." }
}
```

#### POST /api/v1/auth/login
```json
Request:  { "email": "john@example.com", "password": "..." }
Response: { "access_token": "...", "refresh_token": "...", "user": {...} }
```

### Chat

#### POST /api/v1/chat/message
```json
Request: {
  "message": "What were my previous React projects?",
  "conversation_id": "uuid | null",
  "use_memory": true,
  "stream": true
}

Response (streaming=true): Server-Sent Events
  data: {"type":"memory_context","memories":[...]}
  data: {"type":"chunk","content":"Based on our previous..."}
  data: {"type":"chunk","content":" discussions, you..."}
  data: {"type":"done","finish_reason":"stop"}

Response (streaming=false): {
  "message": { "id":"uuid", "role":"assistant", "content":"..." },
  "conversation_id": "uuid",
  "memories_used": 3,
  "context_tokens": 450,
  "model": "gpt-4o"
}
```

### Memory

#### GET /api/v1/memory/search?query=react+projects&limit=5
```json
Response: [
  {
    "id": "uuid",
    "content": "User has been working on a React portfolio app...",
    "importance_score": 0.85,
    "tags": ["react", "projects", "portfolio"],
    "similarity_score": 0.92,
    "created_at": "2024-01-15T..."
  }
]
```

#### GET /api/v1/memory/stats
```json
Response: {
  "total_memories": 142,
  "total_conversations": 23,
  "total_messages": 456,
  "avg_importance": 0.62,
  "memories_by_tag": { "python": 45, "react": 38, "projects": 27 },
  "recent_topics": ["FastAPI", "React", "PostgreSQL"]
}
```

---

## Deployment Guide {#deployment}

### Prerequisites
- Docker 24+ and Docker Compose v2
- 4GB RAM minimum (8GB recommended)
- OpenAI API key (or other LLM provider)

### Quick Start (Docker Compose)
```bash
# 1. Clone and configure
git clone https://github.com/your-org/ai-memory-assistant
cd ai-memory-assistant
cp backend/.env.example backend/.env

# 2. Edit .env — set your API keys
nano backend/.env

# 3. Start all services
docker compose up -d

# 4. Run migrations
docker compose exec backend alembic upgrade head

# 5. Access the app
open http://localhost:80
```

### Environment Variables (Required)
| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |
| `SECRET_KEY` | JWT signing secret (32+ chars) | `your-secret-key` |
| `POSTGRES_PASSWORD` | DB password | `secure_password` |
| `LLM_PROVIDER` | LLM backend | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o` |

### Kubernetes Deployment
```bash
# 1. Create namespace
kubectl apply -f k8s/configmaps/configmaps.yaml

# 2. Update secrets with real values
kubectl edit secret backend-secrets -n ai-memory

# 3. Deploy
kubectl apply -f k8s/deployments/deployments.yaml
kubectl apply -f k8s/services/services.yaml

# 4. Monitor
kubectl get pods -n ai-memory -w
```

### Production Checklist
- [ ] Set strong `SECRET_KEY` (32+ random chars)
- [ ] Use external managed PostgreSQL (RDS, Cloud SQL)
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation (ELK/Loki)
- [ ] Enable database backups
- [ ] Set CORS_ORIGINS to your domain
- [ ] Rotate secrets regularly

---

## User Manual {#user-manual}

### Getting Started
1. **Register** at `/register` with username, email, and password
2. **Login** at `/login`
3. **Start chatting** — the AI will remember everything important

### Chat Features
| Feature | How to Use |
|---------|------------|
| **New conversation** | Click "New Chat" in sidebar |
| **Copy message** | Hover over message → Copy icon |
| **Edit & resubmit** | Hover over your message → Edit icon |
| **Regenerate response** | Hover over AI message → Regenerate icon |
| **Toggle memory** | Click "Memory Active" button in input area |
| **View retrieved memories** | Click "X memories retrieved" above AI message |

### Memory Vault
- Access via the **Brain icon** in the top right
- **Search**: Type 3+ characters for semantic search
- **Filter by tag**: Click tag badges to filter
- **Delete memory**: Click trash icon on memory card
- **Bulk delete**: Select memories → Delete button

### Tips for Better Memory
- Mention specific project names, technologies, goals
- State preferences explicitly ("I prefer TypeScript over JavaScript")
- Reference past discussions ("like we discussed last time")
- The AI ignores small talk but remembers technical content

---

## Testing Strategy {#testing}

### Test Matrix

| Test Type | Tool | Coverage Target |
|-----------|------|----------------|
| Unit | pytest | 80%+ |
| Integration | pytest + httpx | API endpoints |
| Load | locust | 100 concurrent users |
| Security | bandit + pip-audit | No high/critical |
| RAG Eval | Custom | Precision@5 > 0.75 |
| Hallucination | Custom | Rate < 5% |

### Running Tests
```bash
cd backend

# Unit tests
pytest tests/unit/ -v --cov=app

# Integration tests (requires running services)
pytest tests/integration/ -v

# RAG evaluation
python tests/rag/evaluate_retrieval.py

# Load test
pip install locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### RAG Evaluation Metrics
- **Retrieval Precision@K**: Relevant memories / Total retrieved
- **Retrieval Recall@K**: Relevant found / Total relevant  
- **Context Precision**: How much retrieved context is actually used
- **Faithfulness**: Response grounded in retrieved context (no hallucination)
- **Answer Relevancy**: Response relevance to original query

Target: Precision@5 > 0.75, Recall@5 > 0.70, Faithfulness > 0.85
