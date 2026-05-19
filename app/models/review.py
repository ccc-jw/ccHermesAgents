from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    type: Mapped[str]
    phase: Mapped[str]
    status: Mapped[str] = mapped_column(default="open")
    owner_agent: Mapped[str]
    participants_json: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[str] = mapped_column(primary_key=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"))
    reviewer_agent: Mapped[str]
    comment_type: Mapped[str] = mapped_column(default="issue")
    status: Mapped[str] = mapped_column(default="open")
    severity: Mapped[str] = mapped_column(default="minor")
    comment: Mapped[str]
    required_change: Mapped[str | None] = mapped_column(default=None)
    related_artifact: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
