from fastapi.testclient import TestClient

from app.main import create_app


def test_feishu_event_challenge_response():
    client = TestClient(create_app())
    response = client.post("/api/feishu/events", json={"type": "url_verification", "challenge": "abc"})

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc"}
