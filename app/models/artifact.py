from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), default=None)
    source_task_run_id: Mapped[str | None] = mapped_column(ForeignKey("task_runs.id"), default=None)
    artifact_type: Mapped[str]
    name: Mapped[str]
    path: Mapped[str]
    logical_path: Mapped[str | None] = mapped_column(default=None)
    version: Mapped[str] = mapped_column(default="v1")
    status: Mapped[str] = mapped_column(default="active")
    created_by: Mapped[str]
    checksum: Mapped[str | None] = mapped_column(default=None)
    content_type: Mapped[str | None] = mapped_column(default=None)
    size_bytes: Mapped[int | None] = mapped_column(default=None)
    storage_backend: Mapped[str] = mapped_column(default="local")
    is_final: Mapped[int] = mapped_column(default=0)
    parent_artifact_id: Mapped[str | None] = mapped_column(default=None)
    metadata_json: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str]
    updated_at: Mapped[str]
