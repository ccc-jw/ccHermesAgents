from enum import StrEnum

from pydantic import BaseModel, Field


class RunnerStatus(StrEnum):
    CREATED = "CREATED"
    PREPARING_WORKSPACE = "PREPARING_WORKSPACE"
    BUILDING_CONTEXT = "BUILDING_CONTEXT"
    RUNNING = "RUNNING"
    COLLECTING_RESULTS = "COLLECTING_RESULTS"
    PARSING_OUTPUT = "PARSING_OUTPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class TaskContract(BaseModel):
    task_goal: str
    role: str
    phase: str
    input_artifacts: list[str] = Field(default_factory=list)
    must_read_artifacts: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    quality_gates: list[str] = Field(default_factory=list)
    risk_controls: list[str] = Field(default_factory=list)
    review_required: bool = True
    max_changed_files: int | None = None
    timeout_seconds: int | None = None


class RunnerArtifact(BaseModel):
    artifact_type: str
    name: str
    path: str
    checksum: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None


class RunnerResult(BaseModel):
    status: RunnerStatus
    exit_code: int | None = None
    summary: str = ""
    stdout_path: str | None = None
    stderr_path: str | None = None
    logs_path: str | None = None
    diff_path: str | None = None
    output_manifest_path: str | None = None
    artifacts: list[RunnerArtifact] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
