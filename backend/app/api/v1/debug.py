"""
Debug & Explainability API Endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.debug_service import DebugService

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/latest")
async def get_latest_debug_trace(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get the latest RAG prompt debug trace for the current user."""
    trace = DebugService.get_latest_trace(str(current_user.id))
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No debug traces found. Perform a chat query to generate telemetry.",
        )
    return trace


@router.get("/conversation/{conversation_id}")
async def get_conversation_debug_traces(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """Get all RAG debug traces captured for a specific conversation."""
    return DebugService.get_conversation_traces(
        user_id=str(current_user.id),
        conversation_id=str(conversation_id),
    )


@router.get("/prompt/{prompt_id}")
async def get_prompt_debug_trace(
    prompt_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a specific prompt debug trace by ID."""
    trace = DebugService.get_trace_by_id(
        user_id=str(current_user.id),
        trace_id=prompt_id,
    )
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug trace not found.",
        )
    return trace
