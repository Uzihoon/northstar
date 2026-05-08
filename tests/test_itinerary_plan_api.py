from fastapi.testclient import TestClient

import northstar.api.app as app_module
from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryGenerationDiagnostics, ItineraryPlan
from northstar.agent.planner_service import GeneratedItineraryResult
from northstar.agent.schemas import TripRequest
from northstar.memory.plan_store import (
  ItineraryPlanSummary,
  SavedItineraryPlan,
  StoredItineraryPlan,
)
from northstar.memory.plan_run_store import ItineraryPlanRunRecord
from northstar.rag.schemas import RagContext, RagSource

client = TestClient(app_module.app)


def test_itinerary_plan_endpoints_publish_response_models() -> None:
  schema = app_module.app.openapi()

  create_schema = schema["paths"]["/itinerary-plans"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
  list_schema = schema["paths"]["/itinerary-plans"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
  detail_schema = schema["paths"]["/itinerary-plans/{plan_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
  run_start_schema = schema["paths"]["/itinerary-plan-runs"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
  run_detail_schema = schema["paths"]["/itinerary-plan-runs/{run_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

  assert create_schema["$ref"].endswith("/ItineraryPlanCreateResponse")
  assert list_schema["$ref"].endswith("/ItineraryPlanListResponse")
  assert detail_schema["$ref"].endswith("/StoredItineraryPlanResponse")
  assert run_start_schema["$ref"].endswith("/ItineraryPlanRunStartResponse")
  assert run_detail_schema["$ref"].endswith("/ItineraryPlanRunResponse")


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


def test_create_itinerary_plan_returns_saved_plan(monkeypatch) -> None:
  def fake_generate_and_optionally_save_itinerary(
      *,
      prompt,
      user_slug,
      model,
      client,
      session,
      save=True,
      rag_retriever=None,
  ):
    assert callable(rag_retriever)

    rag_context = RagContext(
      query="Kyoto Japan interests: cafes",
      notes=["Kyoto has quiet cafe breaks near the Philosopher's Path."],
      sources=[
        RagSource(
          chunk_id="chunk-1",
          source_path="rag_docs/japan/kyoto/cafes.md",
          score=0.88,
          metadata={"country": "japan", "city": "kyoto"},
        )
      ],
    )

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
      itinerary_diagnostics=ItineraryGenerationDiagnostics(
        repair_attempted=True,
        repair_succeeded=True,
        initial_validation_error="days.0.timeline_items.0: fixed",
      ),
      saved=SavedItineraryPlan(
        trip_request_id="trip-123",
        plan_id="plan-123",
      ),
      rag_context=rag_context,
    )

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
  assert data["itinerary_diagnostics"]["repair_attempted"] is True
  assert data["rag_context"]["sources"][0]["source_path"] == "rag_docs/japan/kyoto/cafes.md"


def test_start_itinerary_plan_run_returns_queued_run(monkeypatch) -> None:
  def fake_create_itinerary_plan_run(
      session,
      *,
      user_slug,
      prompt,
      model_name,
      save=True,
  ):
    assert user_slug == "local"
    assert prompt == "Plan 2 quiet days in Kyoto."
    assert model_name == "qwen3.6:27b"
    assert save is True

    return ItineraryPlanRunRecord(
      run_id="run-123",
      original_prompt=prompt,
      model_name=model_name,
      save=save,
      status="queued",
      progress_events=[
        {
          "status": "queued",
          "message": "Itinerary planning run queued.",
        }
      ],
      error_message=None,
      plan_id=None,
      trip_request_id=None,
      created_at="2026-05-05T10:00:00",
      updated_at="2026-05-05T10:00:00",
    )

  called = {}

  def fake_run_itinerary_plan_job(**kwargs):
    called.update(kwargs)

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "create_itinerary_plan_run", fake_create_itinerary_plan_run)
  monkeypatch.setattr(app_module, "run_itinerary_plan_job", fake_run_itinerary_plan_job)

  response = client.post(
    "/itinerary-plan-runs",
    json={
      "user": "local",
      "prompt": "Plan 2 quiet days in Kyoto.",
      "model": "qwen3.6:27b",
      "save": True,
    },
  )

  assert response.status_code == 200

  data = response.json()
  assert data["run_id"] == "run-123"
  assert data["status"] == "queued"
  assert data["poll_url"] == "/itinerary-plan-runs/run-123?user=local"
  assert data["progress_events"][0]["message"] == "Itinerary planning run queued."
  assert called == {
    "run_id": "run-123",
    "prompt": "Plan 2 quiet days in Kyoto.",
    "user_slug": "local",
    "model": "qwen3.6:27b",
    "save": True,
  }


def test_get_itinerary_plan_run_returns_saved_run(monkeypatch) -> None:
  def fake_get_itinerary_plan_run(session, *, user_slug, run_id):
    assert user_slug == "local"
    assert run_id == "run-123"

    return ItineraryPlanRunRecord(
      run_id="run-123",
      original_prompt="Plan 2 quiet days in Kyoto.",
      model_name="qwen3.6:27b",
      save=True,
      status="completed",
      progress_events=[
        {
          "status": "queued",
          "message": "Itinerary planning run queued.",
        },
        {
          "status": "completed",
          "message": "Itinerary plan completed.",
        },
      ],
      error_message=None,
      plan_id="plan-123",
      trip_request_id="trip-123",
      created_at="2026-05-05T10:00:00",
      updated_at="2026-05-05T10:02:00",
    )

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "get_itinerary_plan_run", fake_get_itinerary_plan_run)

  response = client.get("/itinerary-plan-runs/run-123?user=local")

  assert response.status_code == 200

  data = response.json()
  assert data["run_id"] == "run-123"
  assert data["status"] == "completed"
  assert data["plan_id"] == "plan-123"
  assert data["trip_request_id"] == "trip-123"
  assert data["progress_events"][-1]["status"] == "completed"


def test_get_itinerary_plan_run_returns_404_when_missing(monkeypatch) -> None:
  def fake_get_itinerary_plan_run(session, *, user_slug, run_id):
    return None

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "get_itinerary_plan_run", fake_get_itinerary_plan_run)

  response = client.get("/itinerary-plan-runs/missing-run?user=local")

  assert response.status_code == 404
  assert response.json()["detail"] == "Itinerary planning run not found."


def test_list_itinerary_plans_returns_saved_plan_summaries(monkeypatch) -> None:
  def fake_list_itinerary_plans(session, *, user_slug):
    assert user_slug == "local"

    return [
      ItineraryPlanSummary(
        plan_id="plan-123",
        trip_request_id="trip-123",
        original_prompt="Plan 2 quiet days in Kyoto.",
        title="A relaxed Kyoto plan",
        destination="Kyoto, Japan",
        created_at="2026-05-05T10:00:00",
      )
    ]

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "list_itinerary_plans", fake_list_itinerary_plans)

  response = client.get("/itinerary-plans?user=local")

  assert response.status_code == 200

  data = response.json()
  assert data["plans"][0]["plan_id"] == "plan-123"
  assert data["plans"][0]["trip_request_id"] == "trip-123"
  assert data["plans"][0]["original_prompt"] == "Plan 2 quiet days in Kyoto."
  assert "original_promp" not in data["plans"][0]


def test_get_itinerary_plan_returns_saved_plan_with_rag_context(monkeypatch) -> None:
  def fake_get_itinerary_plan(session, *, user_slug, plan_id):
    assert user_slug == "local"
    assert plan_id == "plan-123"

    return StoredItineraryPlan(
      plan_id="plan-123",
      trip_request_id="trip-123",
      original_prompt="Plan 2 quiet days in Kyoto.",
      trip_request={
        "destination_city": "Kyoto",
        "country": "Japan",
        "duration_days": 2,
      },
      active_context={
        "destination_city": "Kyoto",
        "country": "Japan",
        "duration_days": 2,
        "interests": ["cafes"],
      },
      itinerary={
        "title": "A relaxed Kyoto plan",
        "destination": "Kyoto, Japan",
        "duration_days": 2,
        "preferences_used": ["cafes"],
        "assumptions": [],
        "days": [],
      },
      rag_context={
        "query": "Kyoto Japan interests: cafes",
        "note_hashes": ["sha256:test"],
        "sources": [
          {
            "chunk_id": "chunk-1",
            "source_path": "rag_docs/japan/kyoto/cafes.md",
            "score": 0.88,
            "metadata": {"country": "japan", "city": "kyoto"},
          }
        ],
      },
      itinerary_diagnostics={
        "repair_attempted": True,
        "repair_succeeded": True,
        "initial_validation_error": "days.0.timeline_items.5: fixed",
      },
      model_name="qwen3.6:27b",
      created_at="2026-05-05T10:00:00",
    )

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "get_itinerary_plan", fake_get_itinerary_plan)

  response = client.get("/itinerary-plans/plan-123?user=local")

  assert response.status_code == 200

  data = response.json()
  assert data["plan_id"] == "plan-123"
  assert data["original_prompt"] == "Plan 2 quiet days in Kyoto."
  assert "original_promp" not in data
  assert data["rag_context"]["sources"][0]["source_path"] == "rag_docs/japan/kyoto/cafes.md"
  assert data["rag_context"]["note_hashes"] == ["sha256:test"]
  assert data["itinerary_diagnostics"]["repair_attempted"] is True


def test_get_itinerary_plan_returns_404_when_missing(monkeypatch) -> None:
  def fake_get_itinerary_plan(session, *, user_slug, plan_id):
    return None

  monkeypatch.setattr(app_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(app_module, "get_itinerary_plan", fake_get_itinerary_plan)

  response = client.get("/itinerary-plans/missing-plan?user=local")

  assert response.status_code == 404
  assert response.json()["detail"] == "Itinerary plan not found."
