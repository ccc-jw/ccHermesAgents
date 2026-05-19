from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    source: Mapped[str]
    phase: Mapped[str]
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    severity: Mapped[str] = mapped_column(default="major")
    priority: Mapped[str] = mapped_column(default="normal")
    assigned_agent: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="open")
    created_at: Mapped[str]
    updated_at: Mapped[str]
