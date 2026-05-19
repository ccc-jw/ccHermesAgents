from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    task_contract_id: Mapped[str | None] = mapped_column(ForeignKey("task_contracts.id"), default=None)
    agent_name: Mapped[str]
    runner_type: Mapped[str] = mapped_column(default="claude_code_cli")
    workspace_path: Mapped[str | None] = mapped_column(default=None)
    workspace_strategy: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="CREATED")
    exit_code: Mapped[int | None] = mapped_column(default=None)
    stdout_path: Mapped[str | None] = mapped_column(default=None)
    stderr_path: Mapped[str | None] = mapped_column(default=None)
    logs_path: Mapped[str | None] = mapped_column(default=None)
    diff_path: Mapped[str | None] = mapped_column(default=None)
    summary: Mapped[str | None] = mapped_column(default=None)
    error_code: Mapped[str | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
    result_json: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
    updated_at: Mapped[str]
