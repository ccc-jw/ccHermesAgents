from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.models.review import Review, ReviewComment


class ReviewCommentCreate(BaseModel):
    reviewer_agent: str
    comment_type: str
    status: str = "open"
    severity: str = "minor"
    comment: str
    required_change: str | None = None
    related_artifact: str | None = None


class ReviewService:
    def __init__(self, session: Session):
        self.session = session

    def add_comment(self, review_id: str, request: ReviewCommentCreate) -> dict:
        if self.session.get(Review, review_id) is None:
            raise HTTPException(status_code=404, detail="Review not found")

        comment = ReviewComment(
            id=new_id("comment"),
            review_id=review_id,
            reviewer_agent=request.reviewer_agent,
            comment_type=request.comment_type,
            status=request.status,
            severity=request.severity,
            comment=request.comment,
            required_change=request.required_change,
            related_artifact=request.related_artifact,
            created_at=utc_now_iso(),
        )
        self.session.add(comment)
        self.session.commit()
        return {
            "id": comment.id,
            "review_id": comment.review_id,
            "reviewer_agent": comment.reviewer_agent,
            "status": comment.status,
            "severity": comment.severity,
        }
