from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryGenerationDiagnostics, ItineraryPlan
from northstar.agent.schemas import TripRequest
from northstar.db import Base
from northstar.rag.schemas import RagContext, RagSource
from northstar.memory.plan_store import (
  hash_rag_note,
  get_itinerary_quality_report,
  get_rag_coverage_report,
  get_itinerary_plan,
  list_itinerary_plans,
  save_itinerary_plan,
)


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


def save_sample_plan(
    session: Session,
    user_slug: str = "local",
    rag_context: RagContext | None = None,
    itinerary_diagnostics: ItineraryGenerationDiagnostics | None = None,
):
  return save_itinerary_plan(
    session,
    user_slug=user_slug,
    original_prompt="Plan 2 quiet days in Kyoto.",
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
    model_name="qwen3.6:27b",
    rag_context=rag_context,
    itinerary_diagnostics=itinerary_diagnostics,
  )


def test_list_itinerary_plans_returns_summaries(session: Session) -> None:
  saved = save_sample_plan(session)

  plans = list_itinerary_plans(session, user_slug="local")

  assert len(plans) == 1
  assert plans[0].plan_id == saved.plan_id
  assert plans[0].title == "A relaxed Kyoto plan"
  assert plans[0].destination == "Kyoto, Japan"


def test_get_itinerary_plan_returns_saved_plan(session: Session) -> None:
  saved = save_sample_plan(session)

  plan = get_itinerary_plan(
    session,
    user_slug="local",
    plan_id=saved.plan_id,
  )

  assert plan is not None
  assert plan.plan_id == saved.plan_id
  assert plan.trip_request["destination_city"] == "Kyoto"
  assert plan.active_context["interests"] == ["cafes"]
  assert plan.itinerary["title"] == "A relaxed Kyoto plan"


def test_get_itinerary_plan_returns_none_for_other_user(session: Session) -> None:
  saved = save_sample_plan(session, user_slug="local")

  plan = get_itinerary_plan(
    session,
    user_slug="someone-else",
    plan_id=saved.plan_id,
  )

  assert plan is None

def test_get_itinerary_plan_returns_compact_saved_rag_context(session: Session) -> None:
  note = "Kyoto has quiet cafe breaks near the Philosopher's Path."
  saved = save_sample_plan(
    session,
    rag_context=RagContext(
      query="Kyoto Japan interests: cafes",
      notes=[note],
      sources=[
        RagSource(
          chunk_id="chunk-1",
          source_path="rag_docs/japan/kyoto/cafes.md",
          score=0.88,
          metadata={"country": "japan", "city": "kyoto"},
        )
      ],
    ),
  )

  plan = get_itinerary_plan(
    session,
    user_slug="local",
    plan_id=saved.plan_id,
  )

  assert plan is not None
  assert plan.rag_context is not None
  assert plan.rag_context["query"] == "Kyoto Japan interests: cafes"
  assert plan.rag_context["sources"][0]["source_path"] == "rag_docs/japan/kyoto/cafes.md"
  assert plan.rag_context["note_hashes"] == [hash_rag_note(note)]
  assert "notes" not in plan.rag_context


def test_get_itinerary_plan_returns_saved_itinerary_diagnostics(session: Session) -> None:
  saved = save_sample_plan(
    session,
    itinerary_diagnostics=ItineraryGenerationDiagnostics(
      repair_attempted=True,
      repair_succeeded=True,
      initial_validation_error="days.0.timeline_items.5: fixed",
    ),
  )

  plan = get_itinerary_plan(
    session,
    user_slug="local",
    plan_id=saved.plan_id,
  )

  assert plan is not None
  assert plan.itinerary_diagnostics == {
    "repair_attempted": True,
    "repair_succeeded": True,
    "initial_validation_error": "days.0.timeline_items.5: fixed",
    "quality_status": "ok",
    "quality_issues": [],
  }


def test_get_itinerary_quality_report_counts_warning_codes(session: Session) -> None:
  save_sample_plan(
    session,
    itinerary_diagnostics=ItineraryGenerationDiagnostics(
      quality_status="warning",
      quality_issues=[
        {
          "severity": "warning",
          "code": "possible_misclassified_food_item",
          "path": "days.0.timeline_items.3",
          "message": "Item looks mixed.",
        },
        {
          "severity": "warning",
          "code": "missing_area",
          "path": "days.0.timeline_items.4",
          "message": "Item is missing area.",
        },
      ],
    ),
  )
  save_sample_plan(
    session,
    itinerary_diagnostics=ItineraryGenerationDiagnostics(
      quality_status="warning",
      quality_issues=[
        {
          "severity": "warning",
          "code": "possible_misclassified_food_item",
          "path": "days.1.timeline_items.2",
          "message": "Item looks mixed.",
        },
      ],
    ),
  )
  save_sample_plan(session)

  report = get_itinerary_quality_report(session, user_slug="local")

  assert report.total_plans == 3
  assert report.plans_with_warnings == 2
  assert report.total_issues == 3
  assert report.issue_counts == {
    "possible_misclassified_food_item": 2,
    "missing_area": 1,
  }


def test_get_rag_coverage_report_counts_saved_sources(session: Session) -> None:
  save_sample_plan(
    session,
    rag_context=RagContext(
      query="Kyoto cafes",
      notes=["Cafe notes"],
      sources=[
        RagSource(
          chunk_id="chunk-1",
          source_path="rag_docs/japan/kyoto/cafes.md",
          score=0.9,
          metadata={"country": "japan", "city": "kyoto"},
        ),
        RagSource(
          chunk_id="chunk-2",
          source_path="rag_docs/japan/kyoto/restaurants.md",
          score=0.8,
          metadata={"country": "japan", "city": "kyoto"},
        ),
      ],
    ),
  )
  save_sample_plan(
    session,
    rag_context=RagContext(
      query="Kyoto cafes",
      notes=["More cafe notes"],
      sources=[
        RagSource(
          chunk_id="chunk-3",
          source_path="rag_docs/japan/kyoto/cafes.md",
          score=0.85,
          metadata={"country": "japan", "city": "kyoto"},
        ),
      ],
    ),
  )
  save_sample_plan(session)

  report = get_rag_coverage_report(session, user_slug="local")

  assert report.total_plans == 3
  assert report.plans_with_rag == 2
  assert report.plans_without_rag == 1
  assert report.total_sources == 3
  assert report.source_counts == {
    "rag_docs/japan/kyoto/cafes.md": 2,
    "rag_docs/japan/kyoto/restaurants.md": 1,
  }
