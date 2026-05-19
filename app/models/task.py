from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    phase: Mapped[str]
    owner_agent: Mapped[str]
    task_type: Mapped[str] = mapped_column(default="agent_task")
    runner_type: Mapped[str | None] = mapped_column(default=None)
    workspace_strategy: Mapped[str | None] = mapped_column(default=None)
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="pending")
    priority: Mapped[str] = mapped_column(default="normal")
    risk_level: Mapped[str] = mapped_column(default="normal")
    requires_user_confirmation: Mapped[int] = mapped_column(default=0)
    input_artifacts_json: Mapped[str | None] = mapped_column(default=None)
    expected_artifacts_json: Mapped[str | None] = mapped_column(default=None)
    depends_on_json: Mapped[str | None] = mapped_column(default=None)
    blocked_by_json: Mapped[str | None] = mapped_column(default=None)
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    created_by: Mapped[str]
    assigned_to: Mapped[str | None] = mapped_column(default=None)
    deadline: Mapped[str | None] = mapped_column(default=None)
    deadline_policy: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
    updated_at: Mapped[str]
