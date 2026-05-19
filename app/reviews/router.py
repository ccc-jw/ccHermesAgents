from fastapi import APIRouter

from app.reviews.service import ReviewCommentCreate, ReviewService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/{review_id}/comments")
def add_comment(review_id: str, request: ReviewCommentCreate) -> ApiResponse:
    return ApiResponse(success=True, data=ReviewService().add_comment(review_id, request))
