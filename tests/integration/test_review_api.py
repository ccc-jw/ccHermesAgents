from fastapi.testclient import TestClient

from app.main import create_app


def test_submit_review_comment_returns_open_comment():
    client = TestClient(create_app())
    response = client.post(
        "/api/reviews/review_1/comments",
        json={
            "reviewer_agent": "SEC",
            "comment_type": "issue",
            "status": "open",
            "severity": "major",
            "comment": "Token expiry missing",
            "required_change": "Add token expiry strategy",
            "related_artifact": "artifact_1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "open"
