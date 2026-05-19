from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TaskContract(Base):
    __tablename__ = "task_contracts"

    id: Mapped[str] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    version: Mapped[str] = mapped_column(default="v1")
    task_goal: Mapped[str]
    role: Mapped[str]
    phase: Mapped[str]
    contract_json: Mapped[str]
    created_by: Mapped[str]
    created_at: Mapped[str]
