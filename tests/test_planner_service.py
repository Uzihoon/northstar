from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.agent.planner_service import generate_and_optionally_save_itinerary
from northstar.db import Base
from northstar.memory.models import ItineraryPlanModel, TripRequestModel
from northstar.memory.profile_store import get_or_create_profile_row, get_or_create_user
from northstar.rag.schemas import RagContext, RagSource


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    user = get_or_create_user(db_session, user_slug="local")
    profile = get_or_create_profile_row(db_session, user)
    profile.pace = "relaxed"
    profile.interests = ["cafes", "bookstores"]
    profile.food_preferences = ["vegetarian"]
    db_session.commit()

    yield db_session


class FakeOllamaClient:
  def structured_chat(self, *, messages, model, response_format):
    schema_title = response_format.get("title")

    if schema_title == "TripRequest":
      return {
        "destination_city": "Kyoto",
        "country": "Japan",
        "start_date": None,
        "end_date": None,
        "duration_days": 2,
        "budget_level": None,
        "pace": None,
        "interests": ["quiet vibes"],
        "food_preferences": [],
        "constraints": [],
        "missing_info": ["exact_travel_dates"],
      }

    if schema_title == "ItineraryPlan":
      return {
        "title": "A relaxed Kyoto plan",
        "destination": "Kyoto, Japan",
        "duration_days": 2,
        "preferences_used": ["relaxed", "cafes", "bookstores", "vegetarian"],
        "assumptions": ["Exact dates were not provided."],
        "days": [
          {
            "day_number": 1,
            "date": None,
            "theme": "Quiet Kyoto",
            "timeline_items": [
              {
                "type": "place",
                "start_time": "09:30",
                "end_time": "11:00",
                "time_source": "model_estimate",
                "title": "Philosopher's Path",
                "description": "A calm morning walk.",
                "preference_match": ["relaxed"],
                "source_notes": [],
                "place_category": "walking route",
                "indoor_outdoor": "outdoor",
              }
            ],
          }
        ],
      }

    raise AssertionError(f"Unexpected schema: {schema_title}")


def test_generate_and_optionally_save_itinerary_saves_rows(session: Session) -> None:
  result = generate_and_optionally_save_itinerary(
    prompt="Plan 2 quiet days in Kyoto.",
    user_slug="local",
    model="qwen3.6:27b",
    client=FakeOllamaClient(),
    session=session,
    save=True,
  )

  trip_rows = session.scalars(select(TripRequestModel)).all()
  plan_rows = session.scalars(select(ItineraryPlanModel)).all()

  assert result.saved is not None
  assert len(trip_rows) == 1
  assert len(plan_rows) == 1
  assert trip_rows[0].original_prompt == "Plan 2 quiet days in Kyoto."
  assert trip_rows[0].active_context["interests"] == [
    "cafes",
    "bookstores",
    "quiet vibes",
  ]
  assert plan_rows[0].id == result.saved.plan_id
  assert plan_rows[0].itinerary == result.itinerary.model_dump(mode="json")
  assert result.itinerary_diagnostics.repair_attempted is False


def test_generate_and_optionally_save_itinerary_can_skip_saving(session: Session) -> None:
  result = generate_and_optionally_save_itinerary(
    prompt="Plan 2 quiet days in Kyoto.",
    user_slug="local",
    model="qwen3.6:27b",
    client=FakeOllamaClient(),
    session=session,
    save=False,
  )

  trip_rows = session.scalars(select(TripRequestModel)).all()
  plan_rows = session.scalars(select(ItineraryPlanModel)).all()

  assert result.saved is None
  assert trip_rows == []
  assert plan_rows == []
  assert result.itinerary.destination == "Kyoto, Japan"
  assert result.itinerary_diagnostics.repair_attempted is False

def test_generate_and_optionally_save_itinerary_persists_rag_context(session: Session) -> None:
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

  def fake_rag_retriever(session, active_context):
    return rag_context

  result = generate_and_optionally_save_itinerary(
    prompt="Plan 2 quiet days in Kyoto.",
    user_slug="local",
    model="qwen3.6:27b",
    client=FakeOllamaClient(),
    session=session,
    save=True,
    rag_retriever=fake_rag_retriever,
  )

  plan_rows = session.scalars(select(ItineraryPlanModel)).all()

  assert result.rag_context == rag_context
  assert plan_rows[0].rag_context is not None
  assert plan_rows[0].rag_context["sources"][0]["source_path"] == "rag_docs/japan/kyoto/cafes.md"
  assert "notes" not in plan_rows[0].rag_context
  assert plan_rows[0].itinerary_diagnostics == {
    "repair_attempted": False,
    "repair_succeeded": False,
    "initial_validation_error": None,
  }
