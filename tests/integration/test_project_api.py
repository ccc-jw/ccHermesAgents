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
