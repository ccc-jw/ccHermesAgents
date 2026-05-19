from pydantic import BaseModel

from app.core.ids import new_id


class ReviewCommentCreate(BaseModel):
    reviewer_agent: str
    comment_type: str
    status: str = "open"
    severity: str = "minor"
    comment: str
    required_change: str | None = None
    related_artifact: str | None = None


class ReviewService:
    def add_comment(self, review_id: str, request: ReviewCommentCreate) -> dict:
        return {
            "id": new_id("comment"),
            "review_id": review_id,
            "reviewer_agent": request.reviewer_agent,
            "status": request.status,
            "severity": request.severity,
        }
