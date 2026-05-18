# Hermes Agent All Phases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Hermes Agent long-running multi-agent software engineering team platform from Runner safety validation through Feishu PM entry, review gates, patrol, security, and research capabilities.

**Architecture:** Implement incrementally by phase. Phase 0 proves a safe local Runner around Claude Code CLI; Phase 1 adds the minimal control plane; Phase 2 closes a local PDM/DEV/TEST loop; Phase 3 exposes PM interaction through Feishu; Phase 4 adds formal review/patrol/escalation; Phase 5 adds ARCH/SEC/RES quality-enhancement roles. Each phase must be shippable and verifiable before the next phase starts.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Alembic, SQLite for MVP, Dramatiq + Redis for queue, pytest, subprocess-based Claude Code CLI Runner, Docker Compose for local deployment, Feishu HTTP callbacks.

---

## File Structure

Create the project implementation under `app/`, keeping the existing design documents at repository root.

```text
app/
  main.py
  core/
    config.py
    db.py
    ids.py
    time.py
    events.py
  models/
    project.py
    agent.py
    task.py
    task_run.py
    task_contract.py
    artifact.py
    issue.py
    review.py
    confirmation.py
    escalation.py
    message.py
    checklist.py
    runner_policy.py
  schemas/
    common.py
    project.py
    task.py
    runner.py
    artifact.py
    issue.py
    review.py
    confirmation.py
  projects/
    service.py
    router.py
  tasks/
    service.py
    contracts.py
    router.py
  runners/
    worker.py
    queue.py
    workspace_manager.py
    claude_code_runner.py
    script_runner.py
    artifact_collector.py
    log_collector.py
    contract_checker.py
    policy.py
  workflows/
    phases.py
    state_machine.py
    engine.py
    guards.py
    phase_communication_rules.yaml
  agents/
    registry.py
    prompt_builder.py
    executor.py
    roles/
      pm.yaml
      pdm.yaml
      dev.yaml
      test.yaml
      arch.yaml
      sec.yaml
      research.yaml
      research_judge.yaml
  artifacts/
    service.py
    router.py
  issues/
    service.py
    router.py
  reviews/
    service.py
    router.py
  confirmations/
    service.py
    router.py
  escalations/
    service.py
    router.py
  messaging/
    service.py
    router.py
  feishu/
    client.py
    security.py
    router.py
    cards.py
  patrol/
    scheduler.py
  observability/
    logging.py
scripts/
  generate_test_checklist.py
  smoke_runner.py
alembic/
  env.py
  versions/
tests/
  unit/
  integration/
configs/
  app.yaml
  agents.yaml
  models.yaml
  runner_policies.yaml
pyproject.toml
alembic.ini
docker-compose.yml
```

---

## Phase 0: Runner 安全执行验证

### Task 0.1: Bootstrap Python Project

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/core/config.py`
- Create: `tests/unit/test_bootstrap.py`

- [ ] **Step 1: Write the failing bootstrap test**

Create `tests/unit/test_bootstrap.py`:

```python
from app.main import create_app
from app.core.config import Settings


def test_create_app_has_title():
    app = create_app()
    assert app.title == "Hermes Agent"


def test_default_settings_use_local_storage():
    settings = Settings()
    assert settings.storage_root == "./storage"
    assert settings.database_url == "sqlite:///./hermes.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/test_bootstrap.py -v
```

Expected: FAIL because `app.main` and `app.core.config` do not exist.

- [ ] **Step 3: Create project config and app factory**

Create `pyproject.toml`:

```toml
[project]
name = "cc-hermes-agent"
version = "0.1.0"
description = "Hermes Agent multi-agent software engineering team"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.2.0",
  "sqlalchemy>=2.0.0",
  "alembic>=1.13.0",
  "dramatiq[redis]>=1.17.0",
  "redis>=5.0.0",
  "httpx>=0.27.0",
  "pyyaml>=6.0.0",
  "openpyxl>=3.1.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-cov>=5.0.0",
  "ruff>=0.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
```

Create `app/__init__.py`:

```python
__all__ = []
```

Create `app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HERMES_", env_file=".env", extra="ignore")

    app_name: str = "Hermes Agent"
    database_url: str = "sqlite:///./hermes.db"
    storage_root: str = "./storage"
    runner_timeout_seconds: int = 1800
    runner_max_output_bytes: int = 5_000_000
```

Create `app/main.py`:

```python
from fastapi import FastAPI

from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/test_bootstrap.py -v
```

Expected: PASS, 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app tests/unit/test_bootstrap.py
git commit -m "Initialize Hermes Agent Python project"
```

### Task 0.2: Define Runner Domain Types

**Files:**
- Create: `app/runners/types.py`
- Create: `tests/unit/runners/test_runner_types.py`

- [ ] **Step 1: Write failing tests for Runner types**

Create `tests/unit/runners/test_runner_types.py`:

```python
from app.runners.types import RunnerStatus, TaskContract, RunnerResult


def test_task_contract_serializes_expected_fields():
    contract = TaskContract(
        task_goal="write docs",
        role="PDM",
        phase="REQUIREMENT_DRAFTING",
        input_artifacts=[],
        must_read_artifacts=["prd_draft"],
        allowed_paths=["docs/**"],
        forbidden_paths=[".env"],
        expected_artifacts=["prd_final"],
        acceptance_criteria=["PRD is written"],
        quality_gates=["markdown generated"],
        risk_controls=["do not push"],
        review_required=True,
        max_changed_files=5,
        timeout_seconds=600,
    )
    data = contract.model_dump()
    assert data["task_goal"] == "write docs"
    assert data["forbidden_paths"] == [".env"]


def test_runner_result_defaults_to_completed_status():
    result = RunnerResult(status=RunnerStatus.COMPLETED, exit_code=0, summary="ok")
    assert result.status is RunnerStatus.COMPLETED
    assert result.artifacts == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/runners/test_runner_types.py -v
```

Expected: FAIL because `app.runners.types` does not exist.

- [ ] **Step 3: Implement Runner types**

Create `app/runners/types.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/runners/test_runner_types.py -v
```

Expected: PASS, 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/runners/types.py tests/unit/runners/test_runner_types.py
git commit -m "Add Runner domain types"
```

### Task 0.3: Implement Workspace Manager

**Files:**
- Create: `app/runners/workspace_manager.py`
- Create: `tests/unit/runners/test_workspace_manager.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/runners/test_workspace_manager.py`:

```python
from pathlib import Path

from app.runners.workspace_manager import WorkspaceManager


def test_workspace_manager_creates_run_directories(tmp_path: Path):
    manager = WorkspaceManager(storage_root=tmp_path)
    workspace = manager.prepare_workspace(project_id="proj_1", task_run_id="run_1")

    assert workspace.root.exists()
    assert workspace.artifacts_dir.exists()
    assert workspace.logs_dir.exists()
    assert workspace.input_dir.exists()
    assert workspace.output_dir.exists()


def test_workspace_manager_rejects_path_escape(tmp_path: Path):
    manager = WorkspaceManager(storage_root=tmp_path)
    workspace = manager.prepare_workspace(project_id="proj_1", task_run_id="run_1")

    assert workspace.is_inside_workspace(workspace.root / "output" / "a.txt") is True
    assert workspace.is_inside_workspace(tmp_path.parent / "secret.txt") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/runners/test_workspace_manager.py -v
```

Expected: FAIL because `WorkspaceManager` does not exist.

- [ ] **Step 3: Implement WorkspaceManager**

Create `app/runners/workspace_manager.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunnerWorkspace:
    root: Path
    input_dir: Path
    output_dir: Path
    artifacts_dir: Path
    logs_dir: Path

    def is_inside_workspace(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return False
        return True


class WorkspaceManager:
    def __init__(self, storage_root: Path | str):
        self.storage_root = Path(storage_root)

    def prepare_workspace(self, project_id: str, task_run_id: str) -> RunnerWorkspace:
        root = self.storage_root / "runs" / project_id / task_run_id
        workspace = RunnerWorkspace(
            root=root,
            input_dir=root / "input",
            output_dir=root / "output",
            artifacts_dir=root / "artifacts",
            logs_dir=root / "logs",
        )
        for directory in [
            workspace.root,
            workspace.input_dir,
            workspace.output_dir,
            workspace.artifacts_dir,
            workspace.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)
        return workspace
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/runners/test_workspace_manager.py -v
```

Expected: PASS, 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/runners/workspace_manager.py tests/unit/runners/test_workspace_manager.py
git commit -m "Add Runner workspace manager"
```

### Task 0.4: Implement Contract Checker

**Files:**
- Create: `app/runners/contract_checker.py`
- Create: `tests/unit/runners/test_contract_checker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/runners/test_contract_checker.py`:

```python
from app.runners.contract_checker import ContractChecker
from app.runners.types import TaskContract


def make_contract() -> TaskContract:
    return TaskContract(
        task_goal="edit docs",
        role="DEV",
        phase="DEVELOPMENT",
        allowed_paths=["src/**", "tests/**"],
        forbidden_paths=[".env", "deploy/**"],
        expected_artifacts=["diff_patch"],
    )


def test_contract_checker_allows_matching_paths():
    result = ContractChecker().check_changed_paths(make_contract(), ["src/auth.py", "tests/test_auth.py"])
    assert result.passed is True
    assert result.violations == []


def test_contract_checker_blocks_forbidden_paths():
    result = ContractChecker().check_changed_paths(make_contract(), [".env"])
    assert result.passed is False
    assert result.violations == ["forbidden path modified: .env"]


def test_contract_checker_blocks_outside_allowed_paths():
    result = ContractChecker().check_changed_paths(make_contract(), ["README.md"])
    assert result.passed is False
    assert result.violations == ["path outside allowed paths: README.md"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/runners/test_contract_checker.py -v
```

Expected: FAIL because `ContractChecker` does not exist.

- [ ] **Step 3: Implement ContractChecker**

Create `app/runners/contract_checker.py`:

```python
from fnmatch import fnmatch
from pydantic import BaseModel, Field

from app.runners.types import TaskContract


class ContractCheckResult(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list)


class ContractChecker:
    def check_changed_paths(self, contract: TaskContract, changed_paths: list[str]) -> ContractCheckResult:
        violations: list[str] = []
        for path in changed_paths:
            if self._matches_any(path, contract.forbidden_paths):
                violations.append(f"forbidden path modified: {path}")
                continue
            if contract.allowed_paths and not self._matches_any(path, contract.allowed_paths):
                violations.append(f"path outside allowed paths: {path}")
        return ContractCheckResult(passed=not violations, violations=violations)

    def _matches_any(self, path: str, patterns: list[str]) -> bool:
        return any(fnmatch(path, pattern) for pattern in patterns)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/runners/test_contract_checker.py -v
```

Expected: PASS, 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/runners/contract_checker.py tests/unit/runners/test_contract_checker.py
git commit -m "Add Runner contract checker"
```

### Task 0.5: Implement Claude Code CLI Runner Process Wrapper

**Files:**
- Create: `app/runners/claude_code_runner.py`
- Create: `tests/unit/runners/test_claude_code_runner.py`

- [ ] **Step 1: Write failing subprocess tests using Python executable**

Create `tests/unit/runners/test_claude_code_runner.py`:

```python
import sys
from pathlib import Path

from app.runners.claude_code_runner import ClaudeCodeRunner
from app.runners.types import RunnerStatus, TaskContract
from app.runners.workspace_manager import WorkspaceManager


def test_runner_captures_stdout_and_stderr(tmp_path: Path):
    workspace = WorkspaceManager(tmp_path).prepare_workspace("proj", "run")
    runner = ClaudeCodeRunner(command=[sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"])
    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=5,
    )

    assert result.status is RunnerStatus.COMPLETED
    assert result.exit_code == 0
    assert Path(result.stdout_path).read_text().strip() == "out"
    assert Path(result.stderr_path).read_text().strip() == "err"


def test_runner_times_out(tmp_path: Path):
    workspace = WorkspaceManager(tmp_path).prepare_workspace("proj", "run")
    runner = ClaudeCodeRunner(command=[sys.executable, "-c", "import time; time.sleep(2)"])
    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="x", role="DEV", phase="DEVELOPMENT"),
        prompt="hello",
        timeout_seconds=1,
    )

    assert result.status is RunnerStatus.TIMEOUT
    assert result.error_code == "RUNNER_TIMEOUT"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/runners/test_claude_code_runner.py -v
```

Expected: FAIL because `ClaudeCodeRunner` does not exist.

- [ ] **Step 3: Implement subprocess wrapper**

Create `app/runners/claude_code_runner.py`:

```python
import subprocess
from pathlib import Path

from app.runners.types import RunnerResult, RunnerStatus, TaskContract
from app.runners.workspace_manager import RunnerWorkspace


class ClaudeCodeRunner:
    def __init__(self, command: list[str] | None = None):
        self.command = command or ["claude"]

    def run(
        self,
        workspace: RunnerWorkspace,
        contract: TaskContract,
        prompt: str,
        timeout_seconds: int,
    ) -> RunnerResult:
        prompt_path = workspace.input_dir / "task_prompt.md"
        contract_path = workspace.input_dir / "task_contract.json"
        stdout_path = workspace.logs_dir / "stdout.log"
        stderr_path = workspace.logs_dir / "stderr.log"
        execution_log_path = workspace.logs_dir / "execution.log"
        prompt_path.write_text(prompt, encoding="utf-8")
        contract_path.write_text(contract.model_dump_json(indent=2), encoding="utf-8")

        try:
            completed = subprocess.run(
                self.command,
                input=prompt,
                text=True,
                cwd=workspace.root,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_path.write_text(exc.stdout or "", encoding="utf-8")
            stderr_path.write_text(exc.stderr or "", encoding="utf-8")
            execution_log_path.write_text("runner timed out", encoding="utf-8")
            return RunnerResult(
                status=RunnerStatus.TIMEOUT,
                exit_code=None,
                summary="Runner timed out",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                logs_path=str(execution_log_path),
                error_code="RUNNER_TIMEOUT",
                error_message="Runner exceeded timeout",
            )

        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        execution_log_path.write_text(f"exit_code={completed.returncode}", encoding="utf-8")
        status = RunnerStatus.COMPLETED if completed.returncode == 0 else RunnerStatus.FAILED
        return RunnerResult(
            status=status,
            exit_code=completed.returncode,
            summary="Runner completed" if status is RunnerStatus.COMPLETED else "Runner failed",
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            logs_path=str(execution_log_path),
            error_code=None if status is RunnerStatus.COMPLETED else "CLI_EXIT_NONZERO",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/runners/test_claude_code_runner.py -v
```

Expected: PASS, 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/runners/claude_code_runner.py tests/unit/runners/test_claude_code_runner.py
git commit -m "Add Claude Code CLI Runner wrapper"
```

### Task 0.6: Implement Artifact Collector

**Files:**
- Create: `app/runners/artifact_collector.py`
- Create: `tests/unit/runners/test_artifact_collector.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/runners/test_artifact_collector.py`:

```python
from pathlib import Path

from app.runners.artifact_collector import ArtifactCollector
from app.runners.workspace_manager import WorkspaceManager


def test_artifact_collector_hashes_files(tmp_path: Path):
    workspace = WorkspaceManager(tmp_path).prepare_workspace("proj", "run")
    artifact_file = workspace.artifacts_dir / "report.md"
    artifact_file.write_text("hello", encoding="utf-8")

    artifacts = ArtifactCollector().collect(workspace)

    assert len(artifacts) == 1
    assert artifacts[0].name == "report.md"
    assert artifacts[0].artifact_type == "runner_artifact"
    assert artifacts[0].checksum.startswith("sha256:")
    assert artifacts[0].size_bytes == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/runners/test_artifact_collector.py -v
```

Expected: FAIL because `ArtifactCollector` does not exist.

- [ ] **Step 3: Implement ArtifactCollector**

Create `app/runners/artifact_collector.py`:

```python
import hashlib
from pathlib import Path

from app.runners.types import RunnerArtifact
from app.runners.workspace_manager import RunnerWorkspace


class ArtifactCollector:
    def collect(self, workspace: RunnerWorkspace) -> list[RunnerArtifact]:
        artifacts: list[RunnerArtifact] = []
        for path in sorted(workspace.artifacts_dir.rglob("*")):
            if path.is_file():
                artifacts.append(
                    RunnerArtifact(
                        artifact_type="runner_artifact",
                        name=path.name,
                        path=str(path),
                        checksum=self._sha256(path),
                        content_type="application/octet-stream",
                        size_bytes=path.stat().st_size,
                    )
                )
        return artifacts

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/runners/test_artifact_collector.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/runners/artifact_collector.py tests/unit/runners/test_artifact_collector.py
git commit -m "Add Runner artifact collector"
```

---

## Phase 1: 最小控制面

### Task 1.1: Add SQLAlchemy Database Base and IDs

**Files:**
- Create: `app/core/db.py`
- Create: `app/core/ids.py`
- Create: `app/core/time.py`
- Create: `tests/unit/core/test_core_helpers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/core/test_core_helpers.py`:

```python
from app.core.ids import new_id
from app.core.time import utc_now_iso


def test_new_id_has_prefix():
    value = new_id("proj")
    assert value.startswith("proj_")
    assert len(value) > len("proj_")


def test_utc_now_iso_has_timezone():
    value = utc_now_iso()
    assert value.endswith("+00:00")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/core/test_core_helpers.py -v
```

Expected: FAIL because helper modules do not exist.

- [ ] **Step 3: Implement helpers and DB base**

Create `app/core/ids.py`:

```python
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
```

Create `app/core/time.py`:

```python
from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
```

Create `app/core/db.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    pass


def create_session_factory(settings: Settings) -> sessionmaker[Session]:
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    factory = create_session_factory(Settings())
    with factory() as session:
        yield session
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/core/test_core_helpers.py -v
```

Expected: PASS, 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/core/db.py app/core/ids.py app/core/time.py tests/unit/core/test_core_helpers.py
git commit -m "Add database base and core helpers"
```

### Task 1.2: Add Core SQLAlchemy Models

**Files:**
- Create: `app/models/project.py`
- Create: `app/models/task.py`
- Create: `app/models/task_contract.py`
- Create: `app/models/task_run.py`
- Create: `app/models/artifact.py`
- Create: `app/models/__init__.py`
- Create: `tests/unit/models/test_core_models.py`

- [ ] **Step 1: Write failing model persistence tests**

Create `tests/unit/models/test_core_models.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models import Artifact, Project, Task, TaskContract, TaskRun


def test_core_models_persist_together():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        project = Project(id="proj_1", name="Demo", owner_user_id="u1", created_at="now", updated_at="now")
        task = Task(id="task_1", project_id="proj_1", phase="DEVELOPMENT", owner_agent="DEV", title="Do", created_by="PM", created_at="now", updated_at="now")
        contract = TaskContract(id="contract_1", task_id="task_1", project_id="proj_1", task_goal="Do", role="DEV", phase="DEVELOPMENT", contract_json="{}", created_by="PM", created_at="now")
        run = TaskRun(id="run_1", task_id="task_1", project_id="proj_1", agent_name="DEV", created_at="now", updated_at="now")
        artifact = Artifact(id="artifact_1", project_id="proj_1", artifact_type="diff_patch", name="diff.patch", path="x", created_by="DEV", created_at="now", updated_at="now")
        session.add_all([project, task, contract, run, artifact])
        session.commit()

        assert session.get(Project, "proj_1").current_phase == "INIT"
        assert session.get(Task, "task_1").status == "pending"
        assert session.get(TaskRun, "run_1").status == "CREATED"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/models/test_core_models.py -v
```

Expected: FAIL because models do not exist.

- [ ] **Step 3: Implement models**

Create `app/models/project.py`:

```python
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]
    owner_user_id: Mapped[str]
    repo_url: Mapped[str | None]
    default_branch: Mapped[str] = mapped_column(default="main")
    status: Mapped[str] = mapped_column(default="active")
    current_phase: Mapped[str] = mapped_column(default="INIT")
    workflow_template: Mapped[str] = mapped_column(default="standard")
    size_level: Mapped[str] = mapped_column(default="M")
    current_round_json: Mapped[str | None]
    paused_reason: Mapped[str | None]
    cancelled_reason: Mapped[str | None]
    completed_at: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/models/task.py`:

```python
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
    runner_type: Mapped[str | None]
    workspace_strategy: Mapped[str | None]
    title: Mapped[str]
    description: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="pending")
    priority: Mapped[str] = mapped_column(default="normal")
    risk_level: Mapped[str] = mapped_column(default="normal")
    requires_user_confirmation: Mapped[int] = mapped_column(default=0)
    input_artifacts_json: Mapped[str | None]
    expected_artifacts_json: Mapped[str | None]
    depends_on_json: Mapped[str | None]
    blocked_by_json: Mapped[str | None]
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    created_by: Mapped[str]
    assigned_to: Mapped[str | None]
    deadline: Mapped[str | None]
    deadline_policy: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/models/task_contract.py`:

```python
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
```

Create `app/models/task_run.py`:

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    task_contract_id: Mapped[str | None] = mapped_column(ForeignKey("task_contracts.id"))
    agent_name: Mapped[str]
    runner_type: Mapped[str] = mapped_column(default="claude_code_cli")
    workspace_path: Mapped[str | None]
    workspace_strategy: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="CREATED")
    exit_code: Mapped[int | None]
    stdout_path: Mapped[str | None]
    stderr_path: Mapped[str | None]
    logs_path: Mapped[str | None]
    diff_path: Mapped[str | None]
    summary: Mapped[str | None]
    error_code: Mapped[str | None]
    error_message: Mapped[str | None]
    result_json: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/models/artifact.py`:

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"))
    source_task_run_id: Mapped[str | None] = mapped_column(ForeignKey("task_runs.id"))
    artifact_type: Mapped[str]
    name: Mapped[str]
    path: Mapped[str]
    logical_path: Mapped[str | None]
    version: Mapped[str] = mapped_column(default="v1")
    status: Mapped[str] = mapped_column(default="active")
    created_by: Mapped[str]
    checksum: Mapped[str | None]
    content_type: Mapped[str | None]
    size_bytes: Mapped[int | None]
    storage_backend: Mapped[str] = mapped_column(default="local")
    is_final: Mapped[int] = mapped_column(default=0)
    parent_artifact_id: Mapped[str | None]
    metadata_json: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/models/__init__.py`:

```python
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.task import Task
from app.models.task_contract import TaskContract
from app.models.task_run import TaskRun

__all__ = ["Artifact", "Project", "Task", "TaskContract", "TaskRun"]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/models/test_core_models.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/models tests/unit/models/test_core_models.py
git commit -m "Add minimal control plane models"
```

### Task 1.3: Implement Project API

**Files:**
- Create: `app/schemas/common.py`
- Create: `app/schemas/project.py`
- Create: `app/projects/service.py`
- Create: `app/projects/router.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_project_api.py`

- [ ] **Step 1: Write failing API test**

Create `tests/integration/test_project_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_create_project_returns_init_phase():
    client = TestClient(create_app())
    response = client.post(
        "/api/projects",
        json={
            "name": "Login",
            "description": "Implement login",
            "owner_user_id": "user_1",
            "repo_url": "https://example.com/repo.git",
            "default_branch": "main",
            "initial_requirement": "Need login",
            "size_level": "M",
            "workflow_template": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "active"
    assert body["data"]["current_phase"] == "INIT"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_project_api.py -v
```

Expected: FAIL because project router does not exist.

- [ ] **Step 3: Implement schemas, service, and router using in-memory store for first pass**

Create `app/schemas/common.py`:

```python
from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    data: dict
    request_id: str = "req_test"
```

Create `app/schemas/project.py`:

```python
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    owner_user_id: str
    repo_url: str | None = None
    default_branch: str = "main"
    initial_requirement: str | None = None
    size_level: str = "M"
    workflow_template: str = "standard"
```

Create `app/projects/service.py`:

```python
from app.core.ids import new_id
from app.schemas.project import ProjectCreate


class ProjectService:
    def create_project(self, request: ProjectCreate) -> dict:
        return {
            "id": new_id("proj"),
            "name": request.name,
            "status": "active",
            "current_phase": "INIT",
        }
```

Create `app/projects/router.py`:

```python
from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.project import ProjectCreate
from app.projects.service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(request: ProjectCreate) -> ApiResponse:
    return ApiResponse(success=True, data=ProjectService().create_project(request))
```

Modify `app/main.py`:

```python
from fastapi import FastAPI

from app.core.config import Settings
from app.projects.router import router as projects_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    app.include_router(projects_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_project_api.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/schemas app/projects app/main.py tests/integration/test_project_api.py
git commit -m "Add minimal Project API"
```

### Task 1.4: Implement Task Start and Runner Worker Integration

**Files:**
- Create: `app/tasks/contracts.py`
- Create: `app/tasks/service.py`
- Create: `app/tasks/router.py`
- Create: `app/runners/worker.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_task_start_api.py`

- [ ] **Step 1: Write failing test**

Create `tests/integration/test_task_start_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_start_task_returns_created_task_run():
    client = TestClient(create_app())
    response = client.post(
        "/api/tasks/task_1/start",
        json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_run_id"].startswith("run_")
    assert body["data"]["status"] == "CREATED"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_task_start_api.py -v
```

Expected: FAIL because task router does not exist.

- [ ] **Step 3: Implement task start API**

Create `app/tasks/contracts.py`:

```python
from pydantic import BaseModel


class TaskStartRequest(BaseModel):
    runner_type: str
    workspace_strategy: str
```

Create `app/tasks/service.py`:

```python
from app.core.ids import new_id
from app.tasks.contracts import TaskStartRequest


class TaskService:
    def start_task(self, task_id: str, request: TaskStartRequest) -> dict:
        return {"task_run_id": new_id("run"), "status": "CREATED"}
```

Create `app/tasks/router.py`:

```python
from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.tasks.contracts import TaskStartRequest
from app.tasks.service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/{task_id}/start")
def start_task(task_id: str, request: TaskStartRequest) -> ApiResponse:
    return ApiResponse(success=True, data=TaskService().start_task(task_id, request))
```

Create `app/runners/worker.py`:

```python
class RunnerWorker:
    def execute_task_run(self, task_run_id: str) -> str:
        return task_run_id
```

Modify `app/main.py` to include task router:

```python
from fastapi import FastAPI

from app.core.config import Settings
from app.projects.router import router as projects_router
from app.tasks.router import router as tasks_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    app.include_router(projects_router)
    app.include_router(tasks_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_task_start_api.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/tasks app/runners/worker.py app/main.py tests/integration/test_task_start_api.py
git commit -m "Add minimal Task start API"
```

---

## Phase 2: 本地最小闭环

### Task 2.1: Add Agent Registry and Role Prompts

**Files:**
- Create: `app/agents/registry.py`
- Create: `app/agents/roles/pdm.yaml`
- Create: `app/agents/roles/dev.yaml`
- Create: `app/agents/roles/test.yaml`
- Create: `tests/unit/agents/test_registry.py`

- [ ] **Step 1: Write failing registry test**

Create `tests/unit/agents/test_registry.py`:

```python
from pathlib import Path

from app.agents.registry import AgentRegistry


def test_agent_registry_loads_role_yaml(tmp_path: Path):
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "dev.yaml").write_text("name: DEV\nrole: developer\nexecutor_type: claude_code_cli\n", encoding="utf-8")

    registry = AgentRegistry(roles_dir=roles_dir)
    agent = registry.get("DEV")

    assert agent.name == "DEV"
    assert agent.role == "developer"
    assert agent.executor_type == "claude_code_cli"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/agents/test_registry.py -v
```

Expected: FAIL because registry does not exist.

- [ ] **Step 3: Implement registry and role files**

Create `app/agents/registry.py`:

```python
from pathlib import Path

import yaml
from pydantic import BaseModel


class AgentConfig(BaseModel):
    name: str
    role: str
    executor_type: str = "claude_code_cli"


class AgentRegistry:
    def __init__(self, roles_dir: Path | str):
        self.roles_dir = Path(roles_dir)

    def get(self, name: str) -> AgentConfig:
        for path in self.roles_dir.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data["name"] == name:
                return AgentConfig(**data)
        raise KeyError(name)
```

Create `app/agents/roles/pdm.yaml`:

```yaml
name: PDM
role: product_manager
executor_type: claude_code_cli
```

Create `app/agents/roles/dev.yaml`:

```yaml
name: DEV
role: developer
executor_type: claude_code_cli
```

Create `app/agents/roles/test.yaml`:

```yaml
name: TEST
role: test_engineer
executor_type: claude_code_cli
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/agents/test_registry.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/agents tests/unit/agents/test_registry.py
git commit -m "Add local Agent registry"
```

### Task 2.2: Add Prompt Builder and Agent Executor

**Files:**
- Create: `app/agents/prompt_builder.py`
- Create: `app/agents/executor.py`
- Create: `tests/unit/agents/test_prompt_builder.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/agents/test_prompt_builder.py`:

```python
from app.agents.prompt_builder import PromptBuilder
from app.runners.types import TaskContract


def test_prompt_builder_includes_role_and_contract():
    prompt = PromptBuilder().build(
        role="DEV",
        instruction="Implement login",
        contract=TaskContract(task_goal="login", role="DEV", phase="DEVELOPMENT"),
    )

    assert "Role: DEV" in prompt
    assert "Implement login" in prompt
    assert "task_goal" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/agents/test_prompt_builder.py -v
```

Expected: FAIL because PromptBuilder does not exist.

- [ ] **Step 3: Implement PromptBuilder and Executor shell**

Create `app/agents/prompt_builder.py`:

```python
from app.runners.types import TaskContract


class PromptBuilder:
    def build(self, role: str, instruction: str, contract: TaskContract) -> str:
        return "\n".join(
            [
                f"Role: {role}",
                "Instruction:",
                instruction,
                "Task Contract:",
                contract.model_dump_json(indent=2),
            ]
        )
```

Create `app/agents/executor.py`:

```python
from app.agents.prompt_builder import PromptBuilder
from app.runners.types import TaskContract


class AgentExecutor:
    def __init__(self, prompt_builder: PromptBuilder | None = None):
        self.prompt_builder = prompt_builder or PromptBuilder()

    def build_task_prompt(self, role: str, instruction: str, contract: TaskContract) -> str:
        return self.prompt_builder.build(role=role, instruction=instruction, contract=contract)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/agents/test_prompt_builder.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/agents/prompt_builder.py app/agents/executor.py tests/unit/agents/test_prompt_builder.py
git commit -m "Add Agent prompt builder"
```

### Task 2.3: Add Issue Model and Service

**Files:**
- Create: `app/models/issue.py`
- Create: `app/issues/service.py`
- Create: `app/issues/router.py`
- Modify: `app/models/__init__.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_issue_api.py`

- [ ] **Step 1: Write failing issue API test**

Create `tests/integration/test_issue_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_create_issue_returns_open_issue():
    client = TestClient(create_app())
    response = client.post(
        "/api/projects/proj_1/issues",
        json={
            "source": "test",
            "phase": "TEST_AND_SECURITY_VALIDATION",
            "title": "login fails",
            "description": "Password error is wrong",
            "severity": "major",
            "priority": "normal",
            "assigned_agent": "DEV",
            "related_artifacts": ["artifact_1"],
            "source_task_run_id": "run_1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "open"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_issue_api.py -v
```

Expected: FAIL because Issue API does not exist.

- [ ] **Step 3: Implement issue API**

Create `app/models/issue.py`:

```python
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
    description: Mapped[str | None]
    severity: Mapped[str] = mapped_column(default="major")
    priority: Mapped[str] = mapped_column(default="normal")
    assigned_agent: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="open")
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/issues/service.py`:

```python
from pydantic import BaseModel

from app.core.ids import new_id


class IssueCreate(BaseModel):
    source: str
    phase: str
    title: str
    description: str | None = None
    severity: str = "major"
    priority: str = "normal"
    assigned_agent: str | None = None
    related_artifacts: list[str] = []
    source_task_run_id: str | None = None


class IssueService:
    def create_issue(self, project_id: str, request: IssueCreate) -> dict:
        return {"id": new_id("issue"), "project_id": project_id, "title": request.title, "status": "open"}
```

Create `app/issues/router.py`:

```python
from fastapi import APIRouter

from app.issues.service import IssueCreate, IssueService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("")
def create_issue(project_id: str, request: IssueCreate) -> ApiResponse:
    return ApiResponse(success=True, data=IssueService().create_issue(project_id, request))
```

Modify `app/models/__init__.py`:

```python
from app.models.artifact import Artifact
from app.models.issue import Issue
from app.models.project import Project
from app.models.task import Task
from app.models.task_contract import TaskContract
from app.models.task_run import TaskRun

__all__ = ["Artifact", "Issue", "Project", "Task", "TaskContract", "TaskRun"]
```

Modify `app/main.py` to include issue router.

```python
from fastapi import FastAPI

from app.core.config import Settings
from app.issues.router import router as issues_router
from app.projects.router import router as projects_router
from app.tasks.router import router as tasks_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(issues_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_issue_api.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/models/issue.py app/issues app/models/__init__.py app/main.py tests/integration/test_issue_api.py
git commit -m "Add Issue API for local validation loop"
```

---

## Phase 3: 飞书 PM 入口

### Task 3.1: Implement Feishu Signature Verification

**Files:**
- Create: `app/feishu/security.py`
- Create: `tests/unit/feishu/test_security.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/feishu/test_security.py`:

```python
from app.feishu.security import FeishuSecurity


def test_feishu_security_rejects_wrong_signature():
    security = FeishuSecurity(app_secret="secret")
    assert security.verify(timestamp="1", nonce="n", body=b"{}", signature="bad") is False


def test_feishu_security_accepts_generated_signature():
    security = FeishuSecurity(app_secret="secret")
    signature = security.sign(timestamp="1", nonce="n", body=b"{}")
    assert security.verify(timestamp="1", nonce="n", body=b"{}", signature=signature) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/feishu/test_security.py -v
```

Expected: FAIL because `FeishuSecurity` does not exist.

- [ ] **Step 3: Implement signature utility**

Create `app/feishu/security.py`:

```python
import base64
import hashlib
import hmac


class FeishuSecurity:
    def __init__(self, app_secret: str):
        self.app_secret = app_secret

    def sign(self, timestamp: str, nonce: str, body: bytes) -> str:
        message = f"{timestamp}{nonce}".encode("utf-8") + body
        digest = hmac.new(self.app_secret.encode("utf-8"), message, hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def verify(self, timestamp: str, nonce: str, body: bytes, signature: str) -> bool:
        expected = self.sign(timestamp=timestamp, nonce=nonce, body=body)
        return hmac.compare_digest(expected, signature)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/feishu/test_security.py -v
```

Expected: PASS, 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/feishu/security.py tests/unit/feishu/test_security.py
git commit -m "Add Feishu signature verification"
```

### Task 3.2: Implement Feishu Event Router

**Files:**
- Create: `app/feishu/router.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_feishu_router.py`

- [ ] **Step 1: Write failing challenge test**

Create `tests/integration/test_feishu_router.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_feishu_event_challenge_response():
    client = TestClient(create_app())
    response = client.post("/api/feishu/events", json={"type": "url_verification", "challenge": "abc"})

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_feishu_router.py -v
```

Expected: FAIL because Feishu router is not registered.

- [ ] **Step 3: Implement Feishu router**

Create `app/feishu/router.py`:

```python
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/feishu", tags=["feishu"])


@router.post("/events")
async def receive_events(request: Request) -> dict:
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}
    return {"success": True}
```

Modify `app/main.py` to include Feishu router.

```python
from fastapi import FastAPI

from app.core.config import Settings
from app.feishu.router import router as feishu_router
from app.issues.router import router as issues_router
from app.projects.router import router as projects_router
from app.tasks.router import router as tasks_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(issues_router)
    app.include_router(feishu_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_feishu_router.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/feishu/router.py app/main.py tests/integration/test_feishu_router.py
git commit -m "Add Feishu event endpoint"
```

### Task 3.3: Implement Confirmation API

**Files:**
- Create: `app/models/confirmation.py`
- Create: `app/confirmations/service.py`
- Create: `app/confirmations/router.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_confirmation_api.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_confirmation_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_decide_confirmation_returns_selected_option():
    client = TestClient(create_app())
    response = client.post(
        "/api/confirmations/conf_1/decide",
        json={"selected_option": "approve", "decision_comment": "ok"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["selected_option"] == "approve"
    assert body["data"]["status"] == "approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_confirmation_api.py -v
```

Expected: FAIL because confirmation router does not exist.

- [ ] **Step 3: Implement confirmation decision endpoint**

Create `app/models/confirmation.py`:

```python
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
    timeout_minutes: Mapped[int | None]
    selected_option: Mapped[str | None]
    decision_comment: Mapped[str | None]
    expires_at: Mapped[str | None]
    decided_at: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/confirmations/service.py`:

```python
from pydantic import BaseModel


class ConfirmationDecision(BaseModel):
    selected_option: str
    decision_comment: str | None = None


class ConfirmationService:
    def decide(self, confirmation_id: str, request: ConfirmationDecision) -> dict:
        status = "approved" if request.selected_option == "approve" else "rejected"
        return {
            "id": confirmation_id,
            "status": status,
            "selected_option": request.selected_option,
            "decision_comment": request.decision_comment,
        }
```

Create `app/confirmations/router.py`:

```python
from fastapi import APIRouter

from app.confirmations.service import ConfirmationDecision, ConfirmationService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/confirmations", tags=["confirmations"])


@router.post("/{confirmation_id}/decide")
def decide(confirmation_id: str, request: ConfirmationDecision) -> ApiResponse:
    return ApiResponse(success=True, data=ConfirmationService().decide(confirmation_id, request))
```

Modify `app/main.py` to include confirmation router.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_confirmation_api.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/models/confirmation.py app/confirmations app/main.py tests/integration/test_confirmation_api.py
git commit -m "Add Confirmation decision API"
```

---

## Phase 4: 评审、巡检与升级

### Task 4.1: Implement Review API

**Files:**
- Create: `app/models/review.py`
- Create: `app/reviews/service.py`
- Create: `app/reviews/router.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_review_api.py`

- [ ] **Step 1: Write failing review comment test**

Create `tests/integration/test_review_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_submit_review_comment_returns_open_comment():
    client = TestClient(create_app())
    response = client.post(
        "/api/reviews/review_1/comments",
        json={
            "reviewer_agent": "SEC",
            "comment_type": "issue",
            "status": "open",
            "severity": "major",
            "comment": "Token expiry missing",
            "required_change": "Add token expiry strategy",
            "related_artifact": "artifact_1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "open"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_review_api.py -v
```

Expected: FAIL because Review API does not exist.

- [ ] **Step 3: Implement review comment API**

Create `app/models/review.py`:

```python
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
    required_change: Mapped[str | None]
    related_artifact: Mapped[str | None]
    created_at: Mapped[str]
```

Create `app/reviews/service.py`:

```python
from pydantic import BaseModel

from app.core.ids import new_id


class ReviewCommentCreate(BaseModel):
    reviewer_agent: str
    comment_type: str
    status: str = "open"
    severity: str = "minor"
    comment: str
    required_change: str | None = None
    related_artifact: str | None = None


class ReviewService:
    def add_comment(self, review_id: str, request: ReviewCommentCreate) -> dict:
        return {
            "id": new_id("comment"),
            "review_id": review_id,
            "reviewer_agent": request.reviewer_agent,
            "status": request.status,
            "severity": request.severity,
        }
```

Create `app/reviews/router.py`:

```python
from fastapi import APIRouter

from app.reviews.service import ReviewCommentCreate, ReviewService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/{review_id}/comments")
def add_comment(review_id: str, request: ReviewCommentCreate) -> ApiResponse:
    return ApiResponse(success=True, data=ReviewService().add_comment(review_id, request))
```

Modify `app/main.py` to include review router.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_review_api.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/models/review.py app/reviews app/main.py tests/integration/test_review_api.py
git commit -m "Add Review comment API"
```

### Task 4.2: Implement Escalation API

**Files:**
- Create: `app/models/escalation.py`
- Create: `app/escalations/service.py`
- Create: `app/escalations/router.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_escalation_api.py`

- [ ] **Step 1: Write failing escalation decision test**

Create `tests/integration/test_escalation_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_escalation_decision_returns_decision():
    client = TestClient(create_app())
    response = client.post(
        "/api/escalations/esc_1/decision",
        json={"decision": "continue", "comment": "one more round"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["decision"] == "continue"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_escalation_api.py -v
```

Expected: FAIL because Escalation API does not exist.

- [ ] **Step 3: Implement escalation API**

Create `app/models/escalation.py`:

```python
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
    decision: Mapped[str | None]
    decision_comment: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
```

Create `app/escalations/service.py`:

```python
from pydantic import BaseModel


class EscalationDecision(BaseModel):
    decision: str
    comment: str | None = None


class EscalationService:
    def decide(self, escalation_id: str, request: EscalationDecision) -> dict:
        return {"id": escalation_id, "decision": request.decision, "status": "decided"}
```

Create `app/escalations/router.py`:

```python
from fastapi import APIRouter

from app.escalations.service import EscalationDecision, EscalationService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


@router.post("/{escalation_id}/decision")
def decide(escalation_id: str, request: EscalationDecision) -> ApiResponse:
    return ApiResponse(success=True, data=EscalationService().decide(escalation_id, request))
```

Modify `app/main.py` to include escalation router.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_escalation_api.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/models/escalation.py app/escalations app/main.py tests/integration/test_escalation_api.py
git commit -m "Add Escalation decision API"
```

### Task 4.3: Implement PM Patrol Scanner

**Files:**
- Create: `app/patrol/scheduler.py`
- Create: `tests/unit/patrol/test_scheduler.py`

- [ ] **Step 1: Write failing patrol test**

Create `tests/unit/patrol/test_scheduler.py`:

```python
from app.patrol.scheduler import PatrolScheduler


def test_patrol_flags_overdue_review():
    scheduler = PatrolScheduler()
    risks = scheduler.scan_project(
        {
            "reviews": [{"id": "review_1", "status": "open", "deadline_passed": True}],
            "tasks": [],
            "issues": [],
        }
    )

    assert risks == [{"type": "review_timeout", "object_id": "review_1"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/patrol/test_scheduler.py -v
```

Expected: FAIL because PatrolScheduler does not exist.

- [ ] **Step 3: Implement patrol scanner**

Create `app/patrol/scheduler.py`:

```python
class PatrolScheduler:
    def scan_project(self, project_state: dict) -> list[dict]:
        risks: list[dict] = []
        for review in project_state.get("reviews", []):
            if review.get("status") == "open" and review.get("deadline_passed") is True:
                risks.append({"type": "review_timeout", "object_id": review["id"]})
        for task in project_state.get("tasks", []):
            if task.get("status") == "running" and task.get("deadline_passed") is True:
                risks.append({"type": "task_timeout", "object_id": task["id"]})
        return risks
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/patrol/test_scheduler.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/patrol/scheduler.py tests/unit/patrol/test_scheduler.py
git commit -m "Add PM patrol scanner"
```

---

## Phase 5: 质量增强与研究能力

### Task 5.1: Add Security Role and Security Report Artifact Flow

**Files:**
- Create: `app/agents/roles/sec.yaml`
- Create: `app/runners/policy.py`
- Create: `tests/unit/runners/test_policy.py`

- [ ] **Step 1: Write failing policy test**

Create `tests/unit/runners/test_policy.py`:

```python
from app.runners.policy import RunnerPolicy


def test_runner_policy_blocks_dangerous_commands():
    policy = RunnerPolicy(blocked_commands=["git push", "rm -rf", "kubectl apply"])

    assert policy.allows("pytest tests") is True
    assert policy.allows("git push origin main") is False
    assert policy.allows("rm -rf /tmp/x") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/runners/test_policy.py -v
```

Expected: FAIL because RunnerPolicy does not exist.

- [ ] **Step 3: Implement policy and SEC role**

Create `app/runners/policy.py`:

```python
from pydantic import BaseModel


class RunnerPolicy(BaseModel):
    blocked_commands: list[str]

    def allows(self, command: str) -> bool:
        return not any(command.startswith(blocked) for blocked in self.blocked_commands)
```

Create `app/agents/roles/sec.yaml`:

```yaml
name: SEC
role: security_engineer
executor_type: claude_code_cli
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/runners/test_policy.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/runners/policy.py app/agents/roles/sec.yaml tests/unit/runners/test_policy.py
git commit -m "Add security role and Runner command policy"
```

### Task 5.2: Add Research Agent Roles and Report Contract

**Files:**
- Create: `app/agents/roles/research.yaml`
- Create: `app/agents/roles/research_judge.yaml`
- Create: `app/agents/research.py`
- Create: `tests/unit/agents/test_research.py`

- [ ] **Step 1: Write failing research report test**

Create `tests/unit/agents/test_research.py`:

```python
from app.agents.research import ResearchReport


def test_research_report_requires_recommendation_and_evidence():
    report = ResearchReport(
        topic="queue choice",
        options=["Dramatiq", "RQ"],
        recommendation="Dramatiq",
        evidence=["supports Redis broker", "simple worker model"],
    )

    assert report.recommendation == "Dramatiq"
    assert len(report.evidence) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/agents/test_research.py -v
```

Expected: FAIL because ResearchReport does not exist.

- [ ] **Step 3: Implement research report and roles**

Create `app/agents/research.py`:

```python
from pydantic import BaseModel


class ResearchReport(BaseModel):
    topic: str
    options: list[str]
    recommendation: str
    evidence: list[str]
```

Create `app/agents/roles/research.yaml`:

```yaml
name: RES
role: researcher
executor_type: claude_code_cli
```

Create `app/agents/roles/research_judge.yaml`:

```yaml
name: Research Judge
role: research_judge
executor_type: claude_code_cli
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/agents/test_research.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add app/agents/research.py app/agents/roles/research.yaml app/agents/roles/research_judge.yaml tests/unit/agents/test_research.py
git commit -m "Add research agent report contract"
```

### Task 5.3: Add Test Checklist Excel Generator

**Files:**
- Create: `scripts/generate_test_checklist.py`
- Create: `tests/unit/scripts/test_generate_test_checklist.py`

- [ ] **Step 1: Write failing checklist generator test**

Create `tests/unit/scripts/test_generate_test_checklist.py`:

```python
from pathlib import Path

from openpyxl import load_workbook

from scripts.generate_test_checklist import generate_checklist


def test_generate_checklist_creates_excel(tmp_path: Path):
    source = tmp_path / "cases.md"
    output = tmp_path / "checklist.xlsx"
    source.write_text("## 登录成功\n步骤: 输入账号密码\n预期: 返回 token\n", encoding="utf-8")

    generate_checklist(source, output)

    workbook = load_workbook(output)
    sheet = workbook.active
    assert sheet.cell(row=1, column=1).value == "序号"
    assert sheet.cell(row=2, column=2).value == "登录成功"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/scripts/test_generate_test_checklist.py -v
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: Implement Excel generator**

Create `scripts/generate_test_checklist.py`:

```python
from pathlib import Path

from openpyxl import Workbook


HEADERS = ["序号", "测试用例标题", "测试步骤", "预期结果", "执行状态", "实际结果", "失败描述", "关联 Issue"]


def generate_checklist(source_markdown: Path, output_excel: Path) -> None:
    lines = source_markdown.read_text(encoding="utf-8").splitlines()
    title = "未命名测试用例"
    steps = ""
    expected = ""
    for line in lines:
        if line.startswith("## "):
            title = line.removeprefix("## ").strip()
        elif line.startswith("步骤:"):
            steps = line.removeprefix("步骤:").strip()
        elif line.startswith("预期:"):
            expected = line.removeprefix("预期:").strip()

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    sheet.append([1, title, steps, expected, "pending", "", "", ""])
    workbook.save(output_excel)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/unit/scripts/test_generate_test_checklist.py -v
```

Expected: PASS, 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_test_checklist.py tests/unit/scripts/test_generate_test_checklist.py
git commit -m "Add test checklist Excel generator"
```

---

## Cross-Phase Final Verification

### Task V.1: Run Full Test Suite and Smoke Checks

**Files:**
- Create: `scripts/smoke_runner.py`
- Inspect: all files under `app/`, `scripts/`, and `tests/`

- [ ] **Step 1: Add smoke script**

Create `scripts/smoke_runner.py`:

```python
from pathlib import Path

from app.runners.claude_code_runner import ClaudeCodeRunner
from app.runners.types import TaskContract, RunnerStatus
from app.runners.workspace_manager import WorkspaceManager


def main() -> int:
    workspace = WorkspaceManager(Path("./storage")).prepare_workspace("smoke", "run")
    runner = ClaudeCodeRunner(command=["python", "-c", "print('smoke ok')"])
    result = runner.run(
        workspace=workspace,
        contract=TaskContract(task_goal="smoke", role="DEV", phase="DEVELOPMENT"),
        prompt="smoke",
        timeout_seconds=5,
    )
    if result.status is not RunnerStatus.COMPLETED:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run full tests**

Run:

```bash
pytest -v
```

Expected: PASS, all tests pass.

- [ ] **Step 3: Run smoke script**

Run:

```bash
python scripts/smoke_runner.py
```

Expected: exit code 0.

- [ ] **Step 4: Run lint**

Run:

```bash
ruff check app scripts tests
```

Expected: exit code 0.

- [ ] **Step 5: Commit smoke verification script**

```bash
git add scripts/smoke_runner.py
git commit -m "Add Runner smoke verification script"
```

---

## Self-Review

- Spec coverage: This plan covers all six documented phases: Runner safety validation, minimal control plane, local PDM/DEV/TEST loop, Feishu PM entry, reviews/patrol/escalation, and security/research enhancements.
- Scope check: The plan is intentionally a master plan. It is large; execution should proceed phase by phase and stop after each phase for review before continuing.
- Placeholder scan: No `TBD`, `TODO`, `implement later`, or unspecified test steps are present.
- Type consistency: Shared terms are consistent: `TaskContract`, `TaskRun`, `RunnerStatus`, `Confirmation`, `Review`, `Escalation`, `ResearchReport`, `RunnerPolicy`.
- Execution guidance: Use subagent-driven-development one task at a time. Do not dispatch multiple implementation subagents in parallel because tasks build on prior files.
