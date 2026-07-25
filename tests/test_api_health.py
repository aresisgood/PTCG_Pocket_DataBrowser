from fastapi.testclient import TestClient

from api.main import create_app


def test_health_returns_ok(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'health.db'}")

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
