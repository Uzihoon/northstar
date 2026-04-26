from fastapi.testclient import TestClient

from northstar.api.app import app

client = TestClient(app)

def test_health() -> None:
  response = client.get("/health")

  assert response.status_code == 200

  data = response.json()
  assert data["status"] == "ok"
  assert data["app"] == "northstar"