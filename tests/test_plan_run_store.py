from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.memory.plan_run_store import (
  complete_itinerary_plan_run,
  create_itinerary_plan_run,
  fail_itinerary_plan_run,
  get_itinerary_plan_run,
  mark_itinerary_plan_run_running,
)


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


def test_create_itinerary_plan_run_starts_queued(session: Session) -> None:
  run = create_itinerary_plan_run(
    session,
    user_slug="local",
    prompt="Plan 2 quiet days in Kyoto.",
    model_name="qwen3.6:27b",
    save=True,
  )

  stored = get_itinerary_plan_run(session, user_slug="local", run_id=run.run_id)

  assert stored is not None
  assert stored.run_id == run.run_id
  assert stored.status == "queued"
  assert stored.original_prompt == "Plan 2 quiet days in Kyoto."
  assert stored.model_name == "qwen3.6:27b"
  assert stored.save is True
  assert stored.progress_events[0]["message"] == "Itinerary planning run queued."


def test_get_itinerary_plan_run_is_scoped_to_user(session: Session) -> None:
  run = create_itinerary_plan_run(
    session,
    user_slug="local",
    prompt="Plan 2 quiet days in Kyoto.",
    model_name="qwen3.6:27b",
  )

  stored = get_itinerary_plan_run(session, user_slug="someone-else", run_id=run.run_id)

  assert stored is None


def test_itinerary_plan_run_can_complete(session: Session) -> None:
  run = create_itinerary_plan_run(
    session,
    user_slug="local",
    prompt="Plan 2 quiet days in Kyoto.",
    model_name="qwen3.6:27b",
  )

  mark_itinerary_plan_run_running(session, run_id=run.run_id)
  complete_itinerary_plan_run(
    session,
    run_id=run.run_id,
    plan_id="plan-123",
    trip_request_id="trip-123",
  )

  stored = get_itinerary_plan_run(session, user_slug="local", run_id=run.run_id)

  assert stored is not None
  assert stored.status == "completed"
  assert stored.plan_id == "plan-123"
  assert stored.trip_request_id == "trip-123"
  assert [event["status"] for event in stored.progress_events] == [
    "queued",
    "running",
    "completed",
  ]


def test_itinerary_plan_run_can_fail(session: Session) -> None:
  run = create_itinerary_plan_run(
    session,
    user_slug="local",
    prompt="Plan 2 quiet days in Kyoto.",
    model_name="qwen3.6:27b",
  )

  fail_itinerary_plan_run(
    session,
    run_id=run.run_id,
    error_message="Ollama is unavailable.",
  )

  stored = get_itinerary_plan_run(session, user_slug="local", run_id=run.run_id)

  assert stored is not None
  assert stored.status == "failed"
  assert stored.error_message == "Ollama is unavailable."
  assert stored.progress_events[-1] == {
    "status": "failed",
    "message": "Ollama is unavailable.",
  }
