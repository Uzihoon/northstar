from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, select

from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryPlan
from northstar.agent.schemas import TripRequest
from northstar.memory.models import ItineraryPlanModel, TripRequestModel
from northstar.memory.profile_store import get_or_create_user
from northstar.rag.schemas import RagContext

@dataclass(frozen=True)
class SavedItineraryPlan:
  trip_request_id: str
  plan_id: str

@dataclass(frozen=True)
class ItineraryPlanSummary:
  plan_id: str
  trip_request_id: str
  original_prompt: str
  title: str
  destination: str
  created_at: str

@dataclass(frozen=True)
class StoredItineraryPlan:
  plan_id: str
  trip_request_id: str
  original_prompt: str
  trip_request: dict[str, object]
  active_context: dict[str, object]
  itinerary: dict[str, object]
  rag_context: dict[str, object] | None
  model_name: str
  created_at: str

def save_itinerary_plan(
    session: Session,
    *,
    user_slug: str,
    original_prompt: str,
    trip_request: TripRequest,
    active_context: ActivePlanContext,
    itinerary: ItineraryPlan,
    model_name: str,
    rag_context: RagContext | None = None,
) -> SavedItineraryPlan:
  user = get_or_create_user(session, user_slug=user_slug)

  trip_row = TripRequestModel(
    user_id=user.id,
    original_prompt=original_prompt,
    extracted_request=trip_request.model_dump(mode="json"),
    active_context = active_context.model_dump(mode="json"),
  )
  session.add(trip_row)
  session.flush()

  plan_row = ItineraryPlanModel(
    trip_request_id=trip_row.id,
    model_name=model_name,
    itinerary=itinerary.model_dump(mode="json"),
    rag_context=rag_context.model_dump(mode="json") if rag_context else None,
  )
  session.add(plan_row)
  session.commit()

  return SavedItineraryPlan(
    trip_request_id=trip_row.id,
    plan_id=plan_row.id,
  )

def list_itinerary_plans(
    session: Session,
    *,
    user_slug: str
) -> list[ItineraryPlanSummary]:
  user = get_or_create_user(session, user_slug=user_slug)

  rows = session.execute(
    select(ItineraryPlanModel, TripRequestModel)
    .join(TripRequestModel, ItineraryPlanModel.trip_request_id == TripRequestModel.id)
    .where(TripRequestModel.user_id == user.id)
    .order_by(desc(ItineraryPlanModel.created_at))
  ).all()

  summaries: list[ItineraryPlanSummary] = []

  for plan_row, trip_row in rows:
    itinerary = plan_row.itinerary or {}
    summaries.append(
      ItineraryPlanSummary(
        plan_id=plan_row.id,
        trip_request_id=trip_row.id,
        original_prompt=trip_row.original_prompt,
        title=str(itinerary.get("title", "")),
        destination=str(itinerary.get("destination", "")),
        created_at=plan_row.created_at.isoformat(),
      )
    )
  
  return summaries

def get_itinerary_plan(
    session: Session,
    *,
    user_slug: str,
    plan_id: str,
) -> StoredItineraryPlan | None:
  user = get_or_create_user(session, user_slug=user_slug)

  row = session.execute(
    select(ItineraryPlanModel, TripRequestModel)
    .join(TripRequestModel, ItineraryPlanModel.trip_request_id == TripRequestModel.id)
    .where(ItineraryPlanModel.id == plan_id)
    .where(TripRequestModel.user_id == user.id)
  ).one_or_none()

  if row is None:
    return None
  
  plan_row, trip_row = row

  return StoredItineraryPlan(
    plan_id=plan_row.id,
    trip_request_id=trip_row.id,
    original_prompt=trip_row.original_prompt,
    trip_request=trip_row.extracted_request,
    active_context=trip_row.active_context,
    itinerary=plan_row.itinerary,
    rag_context=plan_row.rag_context,
    model_name=plan_row.model_name,
    created_at=plan_row.created_at.isoformat(),
  )