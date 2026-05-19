from fastapi.testclient import TestClient

from app.core.time import utc_now_iso
from app.models.project import Project
from app.models.review import Review, ReviewComment
from tests.integration.helpers import build_test_app


def test_submit_review_comment_returns_open_comment(tmp_path):
    app, session_factory = build_test_app(tmp_path)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(Project(id="proj_1", name="Demo", owner_user_id="user_1", created_at=now, updated_at=now))
        session.add(
            Review(
                id="review_1",
                project_id="proj_1",
                type="security",
                phase="REVIEW",
                owner_agent="SEC",
                participants_json="[]",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    client = TestClient(app)
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

    with session_factory() as session:
        comment = session.get(ReviewComment, body["data"]["id"])
        assert comment is not None
        assert comment.comment == "Token expiry missing"
