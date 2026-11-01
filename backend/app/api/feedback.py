"""Feedback collection endpoint for DocExtract."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.models import Feedback
from app.db.session import get_session

router = APIRouter(prefix="/feedback", tags=["feedback"])

SessionDep = Annotated[Session, Depends(get_session)]


class FeedbackCreateRequest(BaseModel):
    job_id: str | None = None
    rating: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    comment: str | None = None
    email: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    status: str = "created"


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreateRequest,
    session: SessionDep,
) -> FeedbackResponse:
    fb = Feedback(
        job_id=payload.job_id,
        rating=payload.rating,
        comment=payload.comment,
        email=payload.email,
    )
    fb.set_tags(payload.tags)
    session.add(fb)
    session.commit()
    session.refresh(fb)

    return FeedbackResponse(id=fb.id or 0, status="created")
