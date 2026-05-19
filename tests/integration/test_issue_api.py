from fastapi.testclient import TestClient

from app.core.time import utc_now_iso
from app.models.issue import Issue
from app.models.project import Project
from tests.integration.helpers import build_test_app


def test_create_issue_returns_open_issue(tmp_path):
    app, session_factory = build_test_app(tmp_path)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(Project(id="proj_1", name="Demo", owner_user_id="user_1", created_at=now, updated_at=now))
        session.commit()

    client = TestClient(app)
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

    with session_factory() as session:
        issue = session.get(Issue, body["data"]["id"])
        assert issue is not None
        assert issue.title == "login fails"
