from fastapi.testclient import TestClient

import northstar.api.app as app_module
from northstar.memory.schemas import UserPreferenceProfile

client = TestClient(app_module.app)


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


def test_get_profile_endpoint_publishes_response_model() -> None:
  schema = app_module.app.openapi()
  response_schema = schema["paths"]["/profile"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

  assert response_schema["$ref"].endswith("/UserPreferenceProfileResponse")


def test_get_profile_returns_saved_preferences(monkeypatch) -> None:
  def fake_load_profile(session, user_slug):
    assert session is fake_session
    assert user_slug == "local"

    return UserPreferenceProfile(
      pace="relaxed",
      budget_level="midrange",
      interests=["quiet cafes", "bookstores"],
      food_preferences=["vegetarian"],
      dislikes=["packed schedules"],
      notes=["prefers neighborhoods over landmarks"],
    )

  fake_session = FakeSession()
  monkeypatch.setattr(app_module, "get_session", lambda: fake_session)
  monkeypatch.setattr(app_module, "load_profile", fake_load_profile)

  response = client.get("/profile?user=local")

  assert response.status_code == 200

  data = response.json()
  assert data == {
    "pace": "relaxed",
    "budget_level": "midrange",
    "interests": ["quiet cafes", "bookstores"],
    "food_preferences": ["vegetarian"],
    "dislikes": ["packed schedules"],
    "notes": ["prefers neighborhoods over landmarks"],
  }
