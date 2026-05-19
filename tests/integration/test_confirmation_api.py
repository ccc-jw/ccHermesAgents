from fastapi.testclient import TestClient

from app.core.time import utc_now_iso
from app.models.confirmation import Confirmation
from app.models.project import Project
from tests.integration.helpers import build_test_app


def test_decide_confirmation_returns_selected_option(tmp_path):
    app, session_factory = build_test_app(tmp_path)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(Project(id="proj_1", name="Demo", owner_user_id="user_1", created_at=now, updated_at=now))
        session.add(
            Confirmation(
                id="conf_1",
                project_id="proj_1",
                confirmation_type="review",
                target_type="task",
                target_id="task_1",
                requested_by="PM",
                requested_to_user_id="user_1",
                options_json='["approve", "reject"]',
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    client = TestClient(app)
    response = client.post(
        "/api/confirmations/conf_1/decide",
        json={"selected_option": "approve", "decision_comment": "ok"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["selected_option"] == "approve"
    assert body["data"]["status"] == "approved"

    with session_factory() as session:
        confirmation = session.get(Confirmation, "conf_1")
        assert confirmation.status == "approved"
        assert confirmation.decision_comment == "ok"
