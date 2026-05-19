import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.runners.claude_code_runner import ClaudeCodeRunner
    from app.runners.types import RunnerStatus, TaskContract
    from app.runners.workspace_manager import WorkspaceManager

    workspace = WorkspaceManager(Path("./storage")).prepare_workspace("smoke", "run")
    runner = ClaudeCodeRunner(command=[sys.executable, "-c", "print('smoke ok')"])
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
