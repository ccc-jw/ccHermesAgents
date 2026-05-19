from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.models.artifact import Artifact
from app.models.task_contract import TaskContract as TaskContractModel
from app.models.task_run import TaskRun
from app.runners.artifact_collector import ArtifactCollector
from app.runners.claude_code_runner import ClaudeCodeRunner
from app.runners.openai_runner import OpenAICompatibleRunner
from app.runners.types import RunnerResult, RunnerStatus, TaskContract
from app.runners.workspace_manager import WorkspaceManager


class RunnerWorker:
    def __init__(
        self,
        settings: Settings | None = None,
        runner: ClaudeCodeRunner | None = None,
        artifact_collector: ArtifactCollector | None = None,
        workspace_manager: WorkspaceManager | None = None,
    ):
        self.settings = settings or Settings()
        self.runner = runner or self._default_runner()
        self.artifact_collector = artifact_collector or ArtifactCollector()
        self.workspace_manager = workspace_manager or WorkspaceManager(self.settings.storage_root)

    def _default_runner(self) -> ClaudeCodeRunner | OpenAICompatibleRunner:
        if self.settings.runner_api_base_url and self.settings.runner_model:
            return OpenAICompatibleRunner(self.settings)
        return ClaudeCodeRunner()

    def execute_task_run(self, session: Session, task_run_id: str) -> RunnerResult:
        task_run = session.get(TaskRun, task_run_id)
        if task_run is None:
            raise KeyError(task_run_id)

        try:
            contract_row = session.get(TaskContractModel, task_run.task_contract_id)
            if contract_row is None:
                raise KeyError(task_run.task_contract_id)

            contract = TaskContract.model_validate_json(contract_row.contract_json)
            workspace = self.workspace_manager.prepare_workspace(task_run.project_id, task_run.id)
            self._update_run(
                session,
                task_run,
                RunnerStatus.PREPARING_WORKSPACE,
                workspace_path=str(workspace.root),
            )
            self._update_run(session, task_run, RunnerStatus.RUNNING)
            result = self.runner.run(
                workspace=workspace,
                contract=contract,
                prompt=contract.task_goal,
                timeout_seconds=contract.timeout_seconds or self.settings.runner_timeout_seconds,
            )
            self._update_run(session, task_run, RunnerStatus.COLLECTING_RESULTS)
            collected_artifacts = self.artifact_collector.collect(workspace)
            result.artifacts.extend(collected_artifacts)
            now = utc_now_iso()
            for runner_artifact in collected_artifacts:
                session.add(
                    Artifact(
                        id=new_id("artifact"),
                        project_id=task_run.project_id,
                        task_id=task_run.task_id,
                        source_task_run_id=task_run.id,
                        artifact_type=runner_artifact.artifact_type,
                        name=runner_artifact.name,
                        path=runner_artifact.path,
                        created_by=task_run.agent_name,
                        checksum=runner_artifact.checksum,
                        content_type=runner_artifact.content_type,
                        size_bytes=runner_artifact.size_bytes,
                        created_at=now,
                        updated_at=now,
                    )
                )
            self._apply_result(task_run, result)
            task_run.updated_at = now
            session.commit()
            return result
        except Exception as exc:
            result = RunnerResult(
                status=RunnerStatus.FAILED,
                summary="Worker failed",
                error_code="WORKER_EXCEPTION",
                error_message=str(exc),
            )
            self._apply_result(task_run, result)
            task_run.updated_at = utc_now_iso()
            session.commit()
            return result

    def _update_run(
        self,
        session: Session,
        task_run: TaskRun,
        status: RunnerStatus,
        workspace_path: str | None = None,
    ) -> None:
        task_run.status = status.value
        if workspace_path is not None:
            task_run.workspace_path = workspace_path
        task_run.updated_at = utc_now_iso()
        session.commit()

    def _apply_result(self, task_run: TaskRun, result: RunnerResult) -> None:
        task_run.status = result.status.value
        task_run.exit_code = result.exit_code
        task_run.stdout_path = result.stdout_path
        task_run.stderr_path = result.stderr_path
        task_run.logs_path = result.logs_path
        task_run.diff_path = result.diff_path
        task_run.summary = result.summary
        task_run.error_code = result.error_code
        task_run.error_message = result.error_message
        task_run.result_json = result.model_dump_json()
