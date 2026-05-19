from app.models.project import Project
from tests.integration.helpers import build_test_app
from fastapi.testclient import TestClient


def test_create_project_returns_init_phase(tmp_path):
    app, session_factory = build_test_app(tmp_path)
    client = TestClient(app)
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

    with session_factory() as session:
        project = session.get(Project, body["data"]["id"])
        assert project is not None
        assert project.name == "Login"
