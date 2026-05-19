from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    type: Mapped[str]
    phase: Mapped[str]
    target_user_id: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending_user_decision")
    summary: Mapped[str]
    options_json: Mapped[str]
    decision: Mapped[str | None] = mapped_column(default=None)
    decision_comment: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
    updated_at: Mapped[str]
