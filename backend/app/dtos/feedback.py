"""Feedback DTOs for user feedback submission."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FeedbackCreateDTO(BaseModel):
    """Request DTO for submitting feedback."""

    category: str = Field(..., min_length=1, max_length=50)
    message: str = Field(..., min_length=10, max_length=5000)
    metadata: Optional[Dict[str, Optional[str]]] = Field(
        default=None,
        max_length=10,
        description="Optional context metadata (e.g., page_url, viewport)",
    )


class FeedbackResponseDTO(BaseModel):
    """Response DTO for feedback submission."""

    success: bool
    message: str
    issue_url: Optional[str] = None


class AdminFeedbackItemDTO(BaseModel):
    """One stored submission for an admin."""

    id: int
    user_id: int
    category: str
    message: str
    metadata: Optional[Dict[str, Optional[str]]] = None
    created_at: datetime
    delivery_status: str
    issue_url: Optional[str] = None
    error_reason: Optional[str] = None


class AdminFeedbackListDTO(BaseModel):
    """Page of stored feedback."""

    items: List[AdminFeedbackItemDTO]
    total: int
