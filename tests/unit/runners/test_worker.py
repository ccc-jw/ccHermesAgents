import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.db import Base
from app.core.time import utc_now_iso
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.task import Task
from app.models.task_contract import TaskContract
from app.models.task_run import TaskRun
from app.runners.openai_runner import OpenAICompatibleRunner
from app.runners.types import RunnerResult, RunnerStatus
from app.runners.worker import RunnerWorker


class FakeRunner:
    def run(self, workspace, contract, prompt, timeout_seconds):
        artifact_path = workspace.artifacts_dir / "result.txt"
        artifact_path.write_text("done", encoding="utf-8")
        return RunnerResult(
            status=RunnerStatus.COMPLETED,
            exit_code=0,
            summary="ok",
            stdout_path=str(workspace.logs_dir / "stdout.log"),
            stderr_path=str(workspace.logs_dir / "stderr.log"),
            logs_path=str(workspace.logs_dir / "execution.log"),
        )


class ExplodingRunner:
    def run(self, workspace, contract, prompt, timeout_seconds):
        raise RuntimeError("boom")


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def seed_run(session):
    now = utc_now_iso()
    session.add(
        Project(
            id="proj_1",
            name="Demo",
            owner_user_id="user_1",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        Task(
            id="task_1",
            project_id="proj_1",
            phase="DEVELOPMENT",
            owner_agent="DEV",
            title="Implement login",
            created_by="PM",
            created_at=now,
            updated_at=now,
        )
    )
    contract = TaskContract(
        id="contract_1",
        task_id="task_1",
        project_id="proj_1",
        task_goal="Implement login",
        role="DEV",
        phase="DEVELOPMENT",
        contract_json=json.dumps(
            {
                "task_goal": "Implement login",
                "role": "DEV",
                "phase": "DEVELOPMENT",
            }
        ),
        created_by="PM",
        created_at=now,
    )
    session.add(contract)
    session.add(
        TaskRun(
            id="run_1",
            task_id="task_1",
            project_id="proj_1",
            task_contract_id="contract_1",
            agent_name="DEV",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()


def test_runner_worker_persists_success_result_and_artifacts(tmp_path):
    Session = build_session()
    with Session() as session:
        seed_run(session)
        worker = RunnerWorker(settings=Settings(storage_root=str(tmp_path)), runner=FakeRunner())

        result = worker.execute_task_run(session, "run_1")

        task_run = session.get(TaskRun, "run_1")
        artifact = session.query(Artifact).one()
        assert result.status is RunnerStatus.COMPLETED
        assert task_run.status == "COMPLETED"
        assert task_run.workspace_path is not None
        assert task_run.result_json is not None
        assert artifact.source_task_run_id == "run_1"
        assert artifact.name == "result.txt"


def test_runner_worker_uses_openai_runner_when_api_is_configured(tmp_path):
    worker = RunnerWorker(
        settings=Settings(
            storage_root=str(tmp_path),
            runner_api_base_url="https://example.test/v1",
            runner_model="test-model",
        )
    )

    assert isinstance(worker.runner, OpenAICompatibleRunner)


def test_runner_worker_persists_exception_failure(tmp_path):
    Session = build_session()
    with Session() as session:
        seed_run(session)
        worker = RunnerWorker(
            settings=Settings(storage_root=str(tmp_path)),
            runner=ExplodingRunner(),
        )

        result = worker.execute_task_run(session, "run_1")

        task_run = session.get(TaskRun, "run_1")
        assert result.status is RunnerStatus.FAILED
        assert task_run.status == "FAILED"
        assert task_run.error_code == "WORKER_EXCEPTION"
