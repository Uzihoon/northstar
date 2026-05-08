from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from northstar.memory.models import ItineraryPlanRunModel
from northstar.memory.profile_store import get_or_create_user

PlanRunStatus = Literal["queued", "running", "completed", "failed"]

@dataclass(frozen=True)
class ItineraryPlanRunRecord:
  run_id: str
  original_prompt: str
  model_name: str
  save: bool
  status: PlanRunStatus
  progress_events: list[dict[str, object]]
  error_message: str | None
  plan_id: str | None
  trip_request_id: str | None
  created_at: str
  updated_at: str

def _event(status: PlanRunStatus, message: str) -> dict[str, object]:
  return {
    "status": status,
    "message": message,
  }

def _record_from_row(row: ItineraryPlanRunModel) -> ItineraryPlanRunRecord:
  return ItineraryPlanRunRecord(
    run_id=row.id,
    original_prompt=row.original_prompt,
    model_name=row.model_name,
    save=row.save,
    status=row.status,  # type: ignore[arg-type]
    progress_events=list(row.progress_events or []),
    error_message=row.error_message,
    plan_id=row.plan_id,
    trip_request_id=row.trip_request_id,
    created_at=row.created_at.isoformat(),
    updated_at=row.updated_at.isoformat(),
  )

def _append_event(row: ItineraryPlanRunModel, status: PlanRunStatus, message: str) -> None:
  row.progress_events = [
    *(row.progress_events or []),
    _event(status, message),
  ]

def create_itinerary_plan_run(
    session: Session,
    *,
    user_slug: str,
    prompt: str,
    model_name: str,
    save: bool = True,
) -> ItineraryPlanRunRecord:
  user = get_or_create_user(session, user_slug=user_slug)

  row = ItineraryPlanRunModel(
    user_id=user.id,
    original_prompt=prompt,
    model_name=model_name,
    save=save,
    status="queued",
    progress_events=[
      _event("queued", "Itinerary planning run queued."),
    ],
  )
  session.add(row)
  session.commit()

  return _record_from_row(row)

def get_itinerary_plan_run(
    session: Session,
    *,
    user_slug: str,
    run_id: str,
) -> ItineraryPlanRunRecord | None:
  user = get_or_create_user(session, user_slug=user_slug)

  row = session.scalar(
    select(ItineraryPlanRunModel)
    .where(ItineraryPlanRunModel.id == run_id)
    .where(ItineraryPlanRunModel.user_id == user.id)
  )

  if row is None:
    return None

  return _record_from_row(row)

def mark_itinerary_plan_run_running(
    session: Session,
    *,
    run_id: str,
) -> ItineraryPlanRunRecord:
  row = session.get_one(ItineraryPlanRunModel, run_id)
  row.status = "running"
  _append_event(row, "running", "Itinerary planning run started.")
  session.commit()

  return _record_from_row(row)

def complete_itinerary_plan_run(
    session: Session,
    *,
    run_id: str,
    plan_id: str | None,
    trip_request_id: str | None,
) -> ItineraryPlanRunRecord:
  row = session.get_one(ItineraryPlanRunModel, run_id)
  row.status = "completed"
  row.error_message = None
  row.plan_id = plan_id
  row.trip_request_id = trip_request_id
  _append_event(row, "completed", "Itinerary plan completed.")
  session.commit()

  return _record_from_row(row)

def fail_itinerary_plan_run(
    session: Session,
    *,
    run_id: str,
    error_message: str,
) -> ItineraryPlanRunRecord:
  row = session.get_one(ItineraryPlanRunModel, run_id)
  row.status = "failed"
  row.error_message = error_message
  _append_event(row, "failed", error_message)
  session.commit()

  return _record_from_row(row)
