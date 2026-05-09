from sqlalchemy.exc import SQLAlchemyError

from northstar.agent.extract import TripExtractionError
from northstar.agent.itinerary import ItineraryGenerationError
from northstar.agent.planner_service import generate_and_optionally_save_itinerary
from northstar.config import get_settings
from northstar.db import get_session
from northstar.memory.plan_run_store import (
  complete_itinerary_plan_run,
  fail_itinerary_plan_run,
  mark_itinerary_plan_run_running,
)
from northstar.ollama_client import OllamaError, get_ollama_client
from northstar.rag.retriever import retrieve_travel_context

def _fail_run_safely(run_id: str, error_message: str) -> None:
  try:
    with get_session() as session:
      fail_itinerary_plan_run(
        session,
        run_id=run_id,
        error_message=error_message,
      )
  except SQLAlchemyError:
    # The caller cannot receive this background exception directly.
    return

def run_itinerary_plan_job(
    *,
    run_id: str,
    prompt: str,
    user_slug: str,
    model: str,
    save: bool = True,
) -> None:
  settings = get_settings()
  client = get_ollama_client()

  try:
    with get_session() as session:
      mark_itinerary_plan_run_running(session, run_id=run_id)

      def rag_retriever(session, active_context):
        return retrieve_travel_context(
          session=session,
          context=active_context,
          client=client,
          embedding_model=settings.embedding_model,
          embedding_dimensions=settings.embedding_dimensions,
          limit=3,
        )

      result = generate_and_optionally_save_itinerary(
        prompt=prompt,
        user_slug=user_slug,
        model=model,
        client=client,
        session=session,
        save=save,
        rag_retriever=rag_retriever,
      )

      complete_itinerary_plan_run(
        session,
        run_id=run_id,
        plan_id=result.saved.plan_id if result.saved else None,
        trip_request_id=result.saved.trip_request_id if result.saved else None,
      )
  except (OllamaError, TripExtractionError, ItineraryGenerationError, SQLAlchemyError) as exc:
    _fail_run_safely(run_id, str(exc))
