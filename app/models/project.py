from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    owner_user_id: Mapped[str]
    repo_url: Mapped[str | None] = mapped_column(default=None)
    default_branch: Mapped[str] = mapped_column(default="main")
    status: Mapped[str] = mapped_column(default="active")
    current_phase: Mapped[str] = mapped_column(default="INIT")
    workflow_template: Mapped[str] = mapped_column(default="standard")
    size_level: Mapped[str] = mapped_column(default="M")
    current_round_json: Mapped[str | None] = mapped_column(default=None)
    paused_reason: Mapped[str | None] = mapped_column(default=None)
    cancelled_reason: Mapped[str | None] = mapped_column(default=None)
    completed_at: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
    updated_at: Mapped[str]
