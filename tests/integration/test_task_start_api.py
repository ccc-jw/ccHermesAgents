from fastapi.testclient import TestClient

from app.core.time import utc_now_iso
from app.models.project import Project
from app.models.task import Task
from app.models.task_contract import TaskContract
from app.models.task_run import TaskRun
from tests.integration.helpers import build_test_app


def test_start_task_returns_created_task_run(tmp_path):
    app, session_factory = build_test_app(tmp_path)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(
            Project(id="proj_1", name="Demo", owner_user_id="user_1", created_at=now, updated_at=now)
        )
        session.add(
            Task(
                id="task_1",
                project_id="proj_1",
                phase="DEVELOPMENT",
                owner_agent="DEV",
                title="Implement login",
                description="Create login endpoint",
                created_by="PM",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    client = TestClient(app)
    response = client.post(
        "/api/tasks/task_1/start",
        json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_run_id"].startswith("run_")
    assert body["data"]["status"] == "CREATED"

    with session_factory() as session:
        task = session.get(Task, "task_1")
        task_run = session.get(TaskRun, body["data"]["task_run_id"])
        assert task.status == "queued"
        assert task_run is not None
        assert task_run.task_contract_id is not None
        assert session.get(TaskContract, task_run.task_contract_id).task_goal == "Implement login"


def test_start_task_returns_404_for_missing_task(tmp_path):
    app, _ = build_test_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/tasks/missing/start",
        json={"runner_type": "claude_code_cli", "workspace_strategy": "git_worktree"},
    )

    assert response.status_code == 404
