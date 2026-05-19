from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.reviews.service import ReviewCommentCreate, ReviewService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/{review_id}/comments")
def add_comment(
    review_id: str, request: ReviewCommentCreate, session: Session = Depends(get_session)
) -> ApiResponse:
    return ApiResponse(success=True, data=ReviewService(session).add_comment(review_id, request))
