from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Confirmation(Base):
    __tablename__ = "confirmations"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    confirmation_type: Mapped[str]
    target_type: Mapped[str]
    target_id: Mapped[str]
    requested_by: Mapped[str]
    requested_to_user_id: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending")
    options_json: Mapped[str]
    timeout_minutes: Mapped[int | None] = mapped_column(default=None)
    selected_option: Mapped[str | None] = mapped_column(default=None)
    decision_comment: Mapped[str | None] = mapped_column(default=None)
    expires_at: Mapped[str | None] = mapped_column(default=None)
    decided_at: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
    updated_at: Mapped[str]
