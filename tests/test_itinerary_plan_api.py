from fastapi.testclient import TestClient

import northstar.api.app as app_module
from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryPlan
from northstar.agent.planner_service import GeneratedItineraryResult
from northstar.agent.schemas import TripRequest
from northstar.memory.plan_store import SavedItineraryPlan

client = TestClient(app_module.app)


def test_create_itinerary_plan_returns_saved_plan(monkeypatch) -> None:
  def fake_generate_and_optionally_save_itinerary(
      *,
      prompt,
      user_slug,
      model,
      client,
      session,
      save=True,
  ):
    return GeneratedItineraryResult(
      trip_request=TripRequest(
        destination_city="Kyoto",
        country="Japan",
        duration_days=2,
      ),
      active_context=ActivePlanContext(
        destination_city="Kyoto",
        country="Japan",
        duration_days=2,
        interests=["cafes"],
      ),
      itinerary=ItineraryPlan(
        title="A relaxed Kyoto plan",
        destination="Kyoto, Japan",
        duration_days=2,
        preferences_used=["cafes"],
        assumptions=[],
        days=[],
      ),
      saved=SavedItineraryPlan(
        trip_request_id="trip-123",
        plan_id="plan-123",
      ),
    )

  class FakeSession:
    def __enter__(self):
      return self

    def __exit__(self, exc_type, exc, tb):
      return False

  monkeypatch.setattr(
    app_module,
    "generate_and_optionally_save_itinerary",
    fake_generate_and_optionally_save_itinerary,
  )
  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())

  response = client.post(
    "/itinerary-plans",
    json={
      "user": "local",
      "prompt": "Plan 2 quiet days in Kyoto.",
      "save": True,
    },
  )

  assert response.status_code == 200

  data = response.json()
  assert data["plan_id"] == "plan-123"
  assert data["trip_request_id"] == "trip-123"
  assert data["trip_request"]["destination_city"] == "Kyoto"
  assert data["active_context"]["interests"] == ["cafes"]
  assert data["itinerary"]["destination"] == "Kyoto, Japan"
