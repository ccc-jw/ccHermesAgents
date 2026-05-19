from fastapi.testclient import TestClient

from app.main import create_app


def test_decide_confirmation_returns_selected_option():
    client = TestClient(create_app())
    response = client.post(
        "/api/confirmations/conf_1/decide",
        json={"selected_option": "approve", "decision_comment": "ok"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["selected_option"] == "approve"
    assert body["data"]["status"] == "approved"
