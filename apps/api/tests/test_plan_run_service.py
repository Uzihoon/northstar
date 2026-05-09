from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import northstar.agent.plan_run_service as service_module
from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import (
  ItineraryGenerationDiagnostics,
  ItineraryGenerationError,
  ItineraryPlan,
)
from northstar.agent.planner_service import GeneratedItineraryResult
from northstar.agent.schemas import TripRequest
from northstar.db import Base
from northstar.memory.plan_run_store import create_itinerary_plan_run, get_itinerary_plan_run
from northstar.memory.plan_store import SavedItineraryPlan


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


class FakeSessionFactory:
  def __init__(self, session: Session):
    self.session = session

  def __call__(self):
    return self.session


def test_run_itinerary_plan_job_completes_run(monkeypatch, session: Session) -> None:
  run = create_itinerary_plan_run(
    session,
    user_slug="local",
    prompt="Plan 2 quiet days in Kyoto.",
    model_name="qwen3.6:27b",
  )

  def fake_generate_and_optionally_save_itinerary(**kwargs):
    return GeneratedItineraryResult(
      trip_request=TripRequest(destination_city="Kyoto", country="Japan", duration_days=2),
      active_context=ActivePlanContext(destination_city="Kyoto", country="Japan", duration_days=2),
      itinerary=ItineraryPlan(
        title="A relaxed Kyoto plan",
        destination="Kyoto, Japan",
        duration_days=2,
        preferences_used=[],
        assumptions=[],
        days=[],
      ),
      itinerary_diagnostics=ItineraryGenerationDiagnostics(),
      saved=SavedItineraryPlan(
        trip_request_id="trip-123",
        plan_id="plan-123",
      ),
    )

  monkeypatch.setattr(service_module, "get_session", FakeSessionFactory(session))
  monkeypatch.setattr(service_module, "get_ollama_client", lambda: object())
  monkeypatch.setattr(
    service_module,
    "generate_and_optionally_save_itinerary",
    fake_generate_and_optionally_save_itinerary,
  )

  service_module.run_itinerary_plan_job(
    run_id=run.run_id,
    prompt="Plan 2 quiet days in Kyoto.",
    user_slug="local",
    model="qwen3.6:27b",
  )

  stored = get_itinerary_plan_run(session, user_slug="local", run_id=run.run_id)

  assert stored is not None
  assert stored.status == "completed"
  assert stored.plan_id == "plan-123"
  assert stored.trip_request_id == "trip-123"


def test_run_itinerary_plan_job_marks_run_failed(monkeypatch, session: Session) -> None:
  run = create_itinerary_plan_run(
    session,
    user_slug="local",
    prompt="Plan 2 quiet days in Kyoto.",
    model_name="qwen3.6:27b",
  )

  def fake_generate_and_optionally_save_itinerary(**kwargs):
    raise ItineraryGenerationError("structured itinerary validation failed")

  monkeypatch.setattr(service_module, "get_session", FakeSessionFactory(session))
  monkeypatch.setattr(service_module, "get_ollama_client", lambda: object())
  monkeypatch.setattr(
    service_module,
    "generate_and_optionally_save_itinerary",
    fake_generate_and_optionally_save_itinerary,
  )

  service_module.run_itinerary_plan_job(
    run_id=run.run_id,
    prompt="Plan 2 quiet days in Kyoto.",
    user_slug="local",
    model="qwen3.6:27b",
  )

  stored = get_itinerary_plan_run(session, user_slug="local", run_id=run.run_id)

  assert stored is not None
  assert stored.status == "failed"
  assert stored.error_message == "structured itinerary validation failed"
