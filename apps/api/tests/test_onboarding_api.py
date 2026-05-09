from fastapi.testclient import TestClient

import northstar.api.app as app_module
from northstar.agent.onboarding import OnboardingTurnResult
from northstar.memory.schemas import UserPreferenceProfile

client = TestClient(app_module.app)


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


def test_onboarding_messages_endpoint_publishes_response_model() -> None:
  schema = app_module.app.openapi()
  response_schema = schema["paths"]["/onboarding/messages"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]

  assert response_schema["$ref"].endswith("/OnboardingTurnResponse")


def test_onboarding_messages_returns_opening_message(monkeypatch) -> None:
  def fake_run_onboarding_turn(*, session, user_slug, messages, model, client):
    assert user_slug == "local"
    assert messages == []
    assert model == "qwen3.6:27b"

    return OnboardingTurnResult(
      assistant_message="Hi, I'm Nori. Ready to talk travel?",
      profile_patch={},
      profile=UserPreferenceProfile(),
      is_complete=False,
      next_focus="intro",
    )

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "run_onboarding_turn", fake_run_onboarding_turn)

  response = client.post(
    "/onboarding/messages",
    json={
      "user": "local",
      "model": "qwen3.6:27b",
      "messages": [],
    },
  )

  assert response.status_code == 200

  data = response.json()
  assert data["assistant_message"] == "Hi, I'm Nori. Ready to talk travel?"
  assert data["profile_patch"] == {}
  assert data["profile"]["interests"] == []
  assert data["is_complete"] is False
  assert data["next_focus"] == "intro"


def test_onboarding_messages_extracts_preferences_from_client_history(monkeypatch) -> None:
  def fake_run_onboarding_turn(*, session, user_slug, messages, model, client):
    assert user_slug == "local"
    assert messages[-1].role == "user"
    assert messages[-1].content == "I loved Kyoto because it was calm and walkable."

    return OnboardingTurnResult(
      assistant_message="That sounds lovely. Do you usually like slower days?",
      profile_patch={
        "set": {"pace": "relaxed"},
        "added": {"interests": ["walkable cities"]},
      },
      profile=UserPreferenceProfile(
        pace="relaxed",
        interests=["walkable cities"],
      ),
      is_complete=False,
      next_focus="food",
    )

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "run_onboarding_turn", fake_run_onboarding_turn)

  response = client.post(
    "/onboarding/messages",
    json={
      "user": "local",
      "messages": [
        {"role": "assistant", "content": "What trip do you still think about?"},
        {"role": "user", "content": "I loved Kyoto because it was calm and walkable."},
      ],
    },
  )

  assert response.status_code == 200

  data = response.json()
  assert data["assistant_message"].startswith("That sounds lovely.")
  assert data["profile_patch"]["set"] == {"pace": "relaxed"}
  assert data["profile"]["pace"] == "relaxed"
  assert data["profile"]["interests"] == ["walkable cities"]
  assert data["next_focus"] == "food"
