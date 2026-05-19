import subprocess

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
