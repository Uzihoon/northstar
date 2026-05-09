import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, select

from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryGenerationDiagnostics, ItineraryPlan
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
  itinerary_diagnostics: dict[str, object] | None
  model_name: str
  created_at: str

@dataclass(frozen=True)
class ItineraryQualityReport:
  total_plans: int
  plans_with_warnings: int
  total_issues: int
  issue_counts: dict[str, int]

@dataclass(frozen=True)
class RagCoverageReport:
  total_plans: int
  plans_with_rag: int
  plans_without_rag: int
  total_sources: int
  source_counts: dict[str, int]

def hash_rag_note(text: str) -> str:
  digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
  return f"sha256:{digest}"

def compact_rag_context_for_storage(
    rag_context: RagContext | None,
) -> dict[str, object] | None:
  if rag_context is None:
    return None

  return {
    "query": rag_context.query,
    "sources": [
      source.model_dump(mode="json")
      for source in rag_context.sources
    ],
    "note_hashes": [
      hash_rag_note(note)
      for note in rag_context.notes
    ],
  }

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
    itinerary_diagnostics: ItineraryGenerationDiagnostics | None = None,
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
    rag_context=compact_rag_context_for_storage(rag_context),
    itinerary_diagnostics=asdict(itinerary_diagnostics) if itinerary_diagnostics else None,
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
    itinerary_diagnostics=plan_row.itinerary_diagnostics,
    model_name=plan_row.model_name,
    created_at=plan_row.created_at.isoformat(),
  )

def get_itinerary_quality_report(
    session: Session,
    *,
    user_slug: str,
) -> ItineraryQualityReport:
  user = get_or_create_user(session, user_slug=user_slug)

  rows = session.scalars(
    select(ItineraryPlanModel)
    .join(TripRequestModel, ItineraryPlanModel.trip_request_id == TripRequestModel.id)
    .where(TripRequestModel.user_id == user.id)
  ).all()

  issue_counts: dict[str, int] = {}
  plans_with_warnings = 0
  total_issues = 0

  for row in rows:
    diagnostics = row.itinerary_diagnostics or {}
    quality_issues = diagnostics.get("quality_issues", [])

    if not isinstance(quality_issues, list) or not quality_issues:
      continue

    plans_with_warnings += 1

    for issue in quality_issues:
      if not isinstance(issue, dict):
        continue

      code = issue.get("code")
      if not isinstance(code, str) or not code:
        code = "unknown"

      total_issues += 1
      issue_counts[code] = issue_counts.get(code, 0) + 1

  return ItineraryQualityReport(
    total_plans=len(rows),
    plans_with_warnings=plans_with_warnings,
    total_issues=total_issues,
    issue_counts=issue_counts,
  )

def get_rag_coverage_report(
    session: Session,
    *,
    user_slug: str,
) -> RagCoverageReport:
  user = get_or_create_user(session, user_slug=user_slug)

  rows = session.scalars(
    select(ItineraryPlanModel)
    .join(TripRequestModel, ItineraryPlanModel.trip_request_id == TripRequestModel.id)
    .where(TripRequestModel.user_id == user.id)
  ).all()

  source_counts: dict[str, int] = {}
  plans_with_rag = 0
  total_sources = 0

  for row in rows:
    rag_context = row.rag_context or {}
    sources = rag_context.get("sources", [])

    if not isinstance(sources, list) or not sources:
      continue

    plans_with_rag += 1

    for source in sources:
      if not isinstance(source, dict):
        continue

      source_path = source.get("source_path")
      if not isinstance(source_path, str) or not source_path:
        source_path = "unknown"

      total_sources += 1
      source_counts[source_path] = source_counts.get(source_path, 0) + 1

  return RagCoverageReport(
    total_plans=len(rows),
    plans_with_rag=plans_with_rag,
    plans_without_rag=len(rows) - plans_with_rag,
    total_sources=total_sources,
    source_counts=source_counts,
  )
