from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryPlan
from northstar.agent.schemas import TripRequest
from northstar.memory.models import ItineraryPlanModel, TripRequestModel
from northstar.memory.profile_store import get_or_create_user

@dataclass(frozen=True)
class SavedItineraryPlan:
  trip_request_id: str
  plan_id: str

def save_itinerary_plan(
    session: Session,
    *,
    user_slug: str,
    original_prompt: str,
    trip_request: TripRequest,
    active_context: ActivePlanContext,
    itinerary: ItineraryPlan,
    model_name: str
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
  )
  session.add(plan_row)
  session.commit()

  return SavedItineraryPlan(
    trip_request_id=trip_row.id,
    plan_id=plan_row.id,
  )