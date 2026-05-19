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
