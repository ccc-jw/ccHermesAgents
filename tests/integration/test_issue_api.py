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
