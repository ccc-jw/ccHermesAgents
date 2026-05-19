from fastapi.testclient import TestClient

from app.main import create_app


def test_escalation_decision_returns_decision():
    client = TestClient(create_app())
    response = client.post(
        "/api/escalations/esc_1/decision",
        json={"decision": "continue", "comment": "one more round"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["decision"] == "continue"
