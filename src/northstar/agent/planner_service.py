from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from northstar.agent.context import ActivePlanContext, build_active_plan_context
from northstar.agent.extract import extract_trip_request
from northstar.agent.itinerary import ItineraryPlan, generate_itinerary_plan
from northstar.agent.schemas import TripRequest
from northstar.memory.plan_store import SavedItineraryPlan, save_itinerary_plan
from northstar.memory.profile_store import load_profile
from northstar.ollama_client import OllamaClient
from northstar.rag.schemas import RagContext

RagRetriever = Callable[[Session, ActivePlanContext], RagContext]

@dataclass(frozen=True)
class GeneratedItineraryResult:
  trip_request: TripRequest
  active_context: ActivePlanContext
  itinerary: ItineraryPlan
  rag_context: RagContext | None = None
  saved: SavedItineraryPlan | None = None

def generate_and_optionally_save_itinerary(
    *,
    prompt: str,
    user_slug: str,
    model: str,
    client: OllamaClient,
    session: Session,
    save: bool = True,
    rag_retriever: RagRetriever | None = None,
) -> GeneratedItineraryResult:
  trip_request = extract_trip_request(
    prompt=prompt,
    model=model,
    client=client,
  )
  profile = load_profile(session, user_slug=user_slug)
  active_context = build_active_plan_context(
    profile=profile,
    trip_request=trip_request
  )
  rag_context = None

  if rag_retriever is not None:
    rag_context = rag_retriever(session, active_context)

  itinerary = generate_itinerary_plan(
    context=active_context,
    model=model,
    client=client,
    rag_context=rag_context,
  )

  saved = None

  if save:
    saved = save_itinerary_plan(
      session=session,
      user_slug=user_slug,
      original_prompt=prompt,
      trip_request=trip_request,
      active_context=active_context,
      itinerary=itinerary,
      rag_context=rag_context,
      model_name=model
    )

  return GeneratedItineraryResult(
    trip_request=trip_request,
    active_context=active_context,
    itinerary=itinerary,
    rag_context=rag_context,
    saved=saved,
  )