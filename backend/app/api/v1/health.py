"""
Health check endpoint for load balancers and Kubernetes probes.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.vector_store.factory import get_vector_store

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    vector_store: str
    llm_provider: str
    embedding_provider: str


@router.get("", response_model=HealthResponse)
async def health_check(
    vector_store=Depends(get_vector_store),
) -> HealthResponse:
    """Liveness probe — checks that core services are reachable."""
    vs_healthy = await vector_store.health_check()

    return HealthResponse(
        status="healthy" if vs_healthy else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        vector_store=f"{settings.VECTOR_STORE_TYPE} ({'ok' if vs_healthy else 'error'})",
        llm_provider=settings.LLM_PROVIDER,
        embedding_provider=settings.EMBEDDING_PROVIDER,
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness probe — returns 200 when app is ready to serve requests."""
    return {"status": "ready"}
