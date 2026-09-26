"""Feedback DTOs for user feedback submission via GitHub Issues."""

from typing import Dict, Optional

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
