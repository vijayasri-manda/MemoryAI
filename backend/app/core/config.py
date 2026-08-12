"""
Core configuration management using pydantic-settings.
All settings can be overridden via environment variables or .env file.
"""

from functools import lru_cache
from typing import Literal, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Memory Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    SECRET_KEY: str = "change-me-in-production-use-32-char-secret"
    ALLOWED_HOSTS: list[str] = ["*"]

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 1 day
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_memory"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Vector Store ──────────────────────────────────────────────────────────
    VECTOR_STORE_TYPE: Literal["chroma", "faiss", "pinecone", "weaviate"] = "chroma"
    VECTOR_STORE_COLLECTION: str = "ai_memory_embeddings"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_HOST: Optional[str] = None
    CHROMA_PORT: int = 8000

    # FAISS
    FAISS_INDEX_PATH: str = "./faiss_index"

    # Pinecone
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX_NAME: str = "ai-memory"

    # Weaviate
    WEAVIATE_URL: Optional[str] = None
    WEAVIATE_API_KEY: Optional[str] = None

    # ── Embedding Model ───────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: Literal["sentence_transformers", "gemini", "openai", "instructor"] = (
        "sentence_transformers"
    )
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384         # MiniLM-L6: 384; bge-large: 1024; ada-002: 1536
    EMBEDDING_BATCH_SIZE: int = 32

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["google", "gemini", "openai", "anthropic", "ollama"] = "google"
    LLM_MODEL: str = "gemini-flash-latest"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    LLM_STREAMING: bool = True
    LLM_TIMEOUT: int = 120

    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None   # for custom endpoints / Azure

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── RAG Pipeline ──────────────────────────────────────────────────────────
    RAG_TOP_K: int = 5                     # number of memories to retrieve
    RAG_SIMILARITY_THRESHOLD: float = 0.45
    RAG_MAX_CONTEXT_TOKENS: int = 2000     # token budget for injected memories
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 128
    RAG_RERANK_ENABLED: bool = True
    RAG_DEDUPE_THRESHOLD: float = 0.92    # cosine sim threshold for deduplication
    RAG_COMPRESS_ENABLED: bool = True

    # ── Memory ────────────────────────────────────────────────────────────────
    MEMORY_MIN_TOKENS: int = 20            # ignore messages shorter than this
    MEMORY_IMPORTANCE_THRESHOLD: float = 0.3
    MEMORY_TTL_DAYS: int = 365             # memory expiration (0 = never)
    MEMORY_SUMMARY_INTERVAL: int = 10     # summarize every N messages

    # ── Redis (optional caching) ───────────────────────────────────────────────
    REDIS_URL: Optional[str] = None

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
