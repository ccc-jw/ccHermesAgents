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
