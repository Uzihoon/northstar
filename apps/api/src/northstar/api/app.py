from typing import Any
from datetime import date

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from northstar.agent.extract import TripExtractionError
from northstar.agent.schemas import BudgetLevel, Pace
from northstar.agent.itinerary import ItineraryGenerationError
from northstar.agent.onboarding import OnboardingMessage, run_onboarding_turn
from northstar.agent.plan_run_service import run_itinerary_plan_job
from northstar.agent.planner_service import generate_and_optionally_save_itinerary
from northstar.agent.profile_extract import PreferenceExtractionError
from northstar.db import get_session
from northstar.config import get_settings
from northstar.destinations.catalog import get_destination, search_destinations
from northstar.destinations.schemas import Destination
from northstar.ollama_client import OllamaError, get_ollama_client
from northstar.memory.plan_store import (
  get_itinerary_quality_report,
  get_itinerary_plan,
  get_rag_coverage_report,
  list_itinerary_plans,
)
from northstar.memory.plan_run_store import create_itinerary_plan_run, get_itinerary_plan_run
from northstar.api.admin import router as admin_router
from northstar.rag.retriever import retrieve_travel_context

app = FastAPI(title="Northstar API")
app.include_router(admin_router)

class ChatRequest(BaseModel):
  prompt: str
  model: str | None = None

class ChatResponse(BaseModel):
  model: str
  message: str

class ItineraryPlanRequest(BaseModel):
  prompt: str
  user: str = "local"
  model: str | None = None
  save: bool = True

class ItineraryPlanRunRequest(BaseModel):
  prompt: str | None = None
  user: str = "local"
  model: str | None = None
  save: bool = True
  destination_ids: list[str] = Field(default_factory=list)
  start_date: date | None = None
  end_date: date | None = None
  budget_level: BudgetLevel | None = None
  pace: Pace | None = None
  interests: list[str] = Field(default_factory=list)
  food_preferences: list[str] = Field(default_factory=list)
  additional_info: str | None = None

class OnboardingTurnRequest(BaseModel):
  user: str = "local"
  model: str | None = None
  messages: list[OnboardingMessage] = Field(default_factory=list)

class ItineraryDiagnosticsResponse(BaseModel):
  repair_attempted: bool
  repair_succeeded: bool
  initial_validation_error: str | None = None
  quality_status: str = "ok"
  quality_issues: list[dict[str, str]] = Field(default_factory=list)

class ItineraryPlanCreateResponse(BaseModel):
  plan_id: str | None = None
  trip_request_id: str | None = None
  trip_request: dict[str, Any]
  active_context: dict[str, Any]
  rag_context: dict[str, Any] | None = None
  itinerary: dict[str, Any]
  itinerary_diagnostics: ItineraryDiagnosticsResponse

class ItineraryPlanSummaryResponse(BaseModel):
  plan_id: str
  trip_request_id: str
  original_prompt: str
  title: str
  destination: str
  created_at: str

class ItineraryPlanListResponse(BaseModel):
  plans: list[ItineraryPlanSummaryResponse]

class StoredItineraryPlanResponse(BaseModel):
  plan_id: str
  trip_request_id: str
  original_prompt: str
  trip_request: dict[str, Any]
  active_context: dict[str, Any]
  itinerary: dict[str, Any]
  model_name: str
  rag_context: dict[str, Any] | None = None
  itinerary_diagnostics: ItineraryDiagnosticsResponse | None = None
  created_at: str

class MobilePlanOptionResponse(BaseModel):
  name: str
  category: str
  area: str | None = None
  why_it_fits: str
  estimated_cost: str | None = None
  reservation_recommended: bool | None = None
  tradeoffs: list[str] = Field(default_factory=list)

class MobilePlanCardResponse(BaseModel):
  kind: str
  time: str
  title: str
  description: str
  area: str | None = None
  tags: list[str] = Field(default_factory=list)
  options: list[MobilePlanOptionResponse] = Field(default_factory=list)

class MobilePlanDayResponse(BaseModel):
  day_number: int
  date: str | None = None
  theme: str
  cards: list[MobilePlanCardResponse] = Field(default_factory=list)

class MobilePlanQualityResponse(BaseModel):
  status: str
  visible_to_user: bool = False
  issue_count: int = 0

class MobileItineraryPlanSummaryResponse(BaseModel):
  plan_id: str
  title: str
  destination: str
  duration_days: int
  status: str
  highlights: list[str] = Field(default_factory=list)
  days: list[MobilePlanDayResponse] = Field(default_factory=list)
  quality: MobilePlanQualityResponse

class ItineraryPlanRunEventResponse(BaseModel):
  status: str
  message: str

class ItineraryPlanRunStartResponse(BaseModel):
  run_id: str
  status: str
  poll_url: str
  progress_events: list[ItineraryPlanRunEventResponse]
  created_at: str
  updated_at: str

class ItineraryPlanRunResponse(BaseModel):
  run_id: str
  original_prompt: str
  model_name: str
  save: bool
  status: str
  progress_events: list[ItineraryPlanRunEventResponse]
  error_message: str | None = None
  plan_id: str | None = None
  trip_request_id: str | None = None
  created_at: str
  updated_at: str

class OnboardingTurnResponse(BaseModel):
  assistant_message: str
  profile_patch: dict[str, Any]
  profile: dict[str, Any]
  is_complete: bool
  next_focus: str

class DestinationResponse(Destination):
  pass

class DestinationListResponse(BaseModel):
  destinations: list[DestinationResponse]

class QualityEvalReportResponse(BaseModel):
  plans_scanned: int
  plans_with_warnings: int
  total_issues: int
  issue_counts: dict[str, int]

class RagCoverageEvalReportResponse(BaseModel):
  plans_scanned: int
  plans_with_rag: int
  plans_without_rag: int
  sources_used: int
  source_counts: dict[str, int]

def build_itinerary_run_prompt(request: ItineraryPlanRunRequest) -> str:
  if request.start_date and request.end_date and request.end_date < request.start_date:
    raise HTTPException(
      status_code=422,
      detail="end_date must be on or after start_date.",
    )

  if request.destination_ids:
    if len(request.destination_ids) > 1:
      raise HTTPException(
        status_code=400,
        detail="Multi-destination planning is not supported yet.",
      )

    destination = get_destination(request.destination_ids[0])
    if destination is None:
      raise HTTPException(status_code=404, detail="Destination not found.")

    prompt_parts = [
      f"Plan a trip to {destination.city}, {destination.country}.",
      f"Selected destination id: {destination.id}.",
      f"Destination summary: {destination.summary}",
      f"Destination vibes: {', '.join(destination.vibes)}.",
    ]

    if request.start_date:
      prompt_parts.append(f"Start date: {request.start_date.isoformat()}.")

    if request.end_date:
      prompt_parts.append(f"End date: {request.end_date.isoformat()}.")

    if request.start_date and request.end_date:
      duration_days = (request.end_date - request.start_date).days + 1
      prompt_parts.append(f"Duration: {duration_days} days.")

    if request.budget_level:
      prompt_parts.append(f"Budget level: {request.budget_level.value}.")

    if request.pace:
      prompt_parts.append(f"Pace: {request.pace.value}.")

    if request.interests:
      prompt_parts.append(f"Interests: {', '.join(request.interests)}.")

    if request.food_preferences:
      prompt_parts.append(f"Food preferences: {', '.join(request.food_preferences)}.")

    if request.additional_info:
      prompt_parts.append(f"Additional information: {request.additional_info}")

    return "\n".join(prompt_parts)

  if request.prompt:
    return request.prompt

  raise HTTPException(
    status_code=422,
    detail="Provide either prompt or destination_ids.",
  )

def _dedupe_strings(values: list[Any], limit: int | None = None) -> list[str]:
  seen: set[str] = set()
  results: list[str] = []

  for value in values:
    if not isinstance(value, str):
      continue

    normalized = value.strip()
    if not normalized or normalized in seen:
      continue

    seen.add(normalized)
    results.append(normalized)

    if limit is not None and len(results) >= limit:
      break

  return results

def _split_category_tags(value: Any) -> list[str]:
  if not isinstance(value, str):
    return []

  return [
    part.strip()
    for part in value.replace("&", "/").split("/")
    if part.strip()
  ]

def _build_mobile_card(item: dict[str, Any]) -> MobilePlanCardResponse:
  kind = str(item.get("type") or "activity")
  start_time = str(item.get("start_time") or "")
  end_time = str(item.get("end_time") or "")
  time = f"{start_time}-{end_time}".strip("-")
  raw_options = item.get("options") if isinstance(item.get("options"), list) else []

  tags = _dedupe_strings(
    [
      kind,
      *_split_category_tags(item.get("place_category")),
      *(item.get("dietary_fit") if isinstance(item.get("dietary_fit"), list) else []),
      *(item.get("preference_match") if isinstance(item.get("preference_match"), list) else []),
    ]
  )

  return MobilePlanCardResponse(
    kind=kind,
    time=time,
    title=str(item.get("title") or ""),
    description=str(item.get("description") or ""),
    area=item.get("area") if isinstance(item.get("area"), str) else None,
    tags=tags,
    options=[
      MobilePlanOptionResponse(
        name=str(option.get("name") or ""),
        category=str(option.get("category") or "option"),
        area=option.get("area") if isinstance(option.get("area"), str) else None,
        why_it_fits=str(option.get("why_it_fits") or ""),
        estimated_cost=option.get("estimated_cost") if isinstance(option.get("estimated_cost"), str) else None,
        reservation_recommended=option.get("reservation_recommended") if isinstance(option.get("reservation_recommended"), bool) else None,
        tradeoffs=[
          str(tradeoff)
          for tradeoff in option.get("tradeoffs", [])
          if isinstance(tradeoff, str)
        ],
      )
      for option in raw_options
      if isinstance(option, dict)
    ],
  )

def _build_mobile_plan_summary(plan) -> MobileItineraryPlanSummaryResponse:
  itinerary = plan.itinerary or {}
  diagnostics = plan.itinerary_diagnostics or {}
  quality_status = str(diagnostics.get("quality_status") or "ok")
  quality_issues = diagnostics.get("quality_issues", [])
  issue_count = len(quality_issues) if isinstance(quality_issues, list) else 0
  raw_days = itinerary.get("days") if isinstance(itinerary.get("days"), list) else []
  active_context = plan.active_context or {}
  highlights = _dedupe_strings(
    itinerary.get("preferences_used") if isinstance(itinerary.get("preferences_used"), list) else [],
    limit=6,
  )

  if not highlights:
    highlights = _dedupe_strings(
      [
        *(active_context.get("interests") if isinstance(active_context.get("interests"), list) else []),
        *(active_context.get("food_preferences") if isinstance(active_context.get("food_preferences"), list) else []),
      ],
      limit=6,
    )

  return MobileItineraryPlanSummaryResponse(
    plan_id=plan.plan_id,
    title=str(itinerary.get("title") or ""),
    destination=str(itinerary.get("destination") or ""),
    duration_days=int(itinerary.get("duration_days") or 0),
    status="ready_with_warnings" if quality_status == "warning" else "ready",
    highlights=highlights,
    days=[
      MobilePlanDayResponse(
        day_number=int(day.get("day_number") or day_index + 1),
        date=day.get("date") if isinstance(day.get("date"), str) else None,
        theme=str(day.get("theme") or ""),
        cards=[
          _build_mobile_card(item)
          for item in day.get("timeline_items", [])
          if isinstance(item, dict)
        ],
      )
      for day_index, day in enumerate(raw_days)
      if isinstance(day, dict)
    ],
    quality=MobilePlanQualityResponse(
      status=quality_status,
      visible_to_user=False,
      issue_count=issue_count,
    ),
  )

@app.get("/health")
def health() -> dict[str, str]:
  settings = get_settings()
  return {
    "status": "ok",
    "app": settings.app_name,
    "environment": settings.environment,
    "ollama_base_url": settings.ollama_base_url,
    "default_model": settings.default_model,
  }

@app.get("/models")
def models() -> dict[str, list[str]]:
  client = get_ollama_client()
  
  try:
    return {"models": client.list_models()}
  except OllamaError as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  client = get_ollama_client()

  try:
    message = client.chat(prompt=request.prompt, model=resolved_model)
  except OllamaError as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  
  return ChatResponse(model=resolved_model, message=message)

@app.get("/destinations", response_model=DestinationListResponse)
def list_destinations(
    q: str | None = None,
    country: str | None = None,
    vibe: str | None = None,
    limit: int = 20,
) -> DestinationListResponse:
  return DestinationListResponse(
    destinations=[
      DestinationResponse.model_validate(destination.model_dump(mode="json"))
      for destination in search_destinations(
        q=q,
        country=country,
        vibe=vibe,
        limit=limit,
      )
    ]
  )

@app.get("/destinations/{destination_id}", response_model=DestinationResponse)
def get_destination_detail(destination_id: str) -> DestinationResponse:
  destination = get_destination(destination_id)

  if destination is None:
    raise HTTPException(status_code=404, detail="Destination not found.")

  return DestinationResponse.model_validate(destination.model_dump(mode="json"))

@app.get("/admin/evals/quality", response_model=QualityEvalReportResponse)
def get_quality_eval_report(user: str = "local") -> QualityEvalReportResponse:
  try:
    with get_session() as session:
      report = get_itinerary_quality_report(session, user_slug=user)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  return QualityEvalReportResponse(
    plans_scanned=report.total_plans,
    plans_with_warnings=report.plans_with_warnings,
    total_issues=report.total_issues,
    issue_counts=report.issue_counts,
  )

@app.get("/admin/evals/rag-coverage", response_model=RagCoverageEvalReportResponse)
def get_rag_coverage_eval_report(user: str = "local") -> RagCoverageEvalReportResponse:
  try:
    with get_session() as session:
      report = get_rag_coverage_report(session, user_slug=user)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  return RagCoverageEvalReportResponse(
    plans_scanned=report.total_plans,
    plans_with_rag=report.plans_with_rag,
    plans_without_rag=report.plans_without_rag,
    sources_used=report.total_sources,
    source_counts=report.source_counts,
  )

@app.post("/onboarding/messages", response_model=OnboardingTurnResponse)
def onboarding_messages(request: OnboardingTurnRequest) -> OnboardingTurnResponse:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  client = get_ollama_client()

  try:
    with get_session() as session:
      result = run_onboarding_turn(
        session=session,
        user_slug=request.user,
        messages=request.messages,
        model=resolved_model,
        client=client,
      )
  except (OllamaError, PreferenceExtractionError) as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  return OnboardingTurnResponse(
    assistant_message=result.assistant_message,
    profile_patch=result.profile_patch,
    profile=result.profile.model_dump(mode="json"),
    is_complete=result.is_complete,
    next_focus=result.next_focus,
  )

@app.post("/itinerary-plan-runs", response_model=ItineraryPlanRunStartResponse)
def start_itinerary_plan_run(
    request: ItineraryPlanRunRequest,
    background_tasks: BackgroundTasks,
) -> ItineraryPlanRunStartResponse:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  prompt = build_itinerary_run_prompt(request)

  try:
    with get_session() as session:
      run = create_itinerary_plan_run(
        session,
        user_slug=request.user,
        prompt=prompt,
        model_name=resolved_model,
        save=request.save,
      )
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  background_tasks.add_task(
    run_itinerary_plan_job,
    run_id=run.run_id,
    prompt=prompt,
    user_slug=request.user,
    model=resolved_model,
    save=request.save,
  )

  return ItineraryPlanRunStartResponse(
    run_id=run.run_id,
    status=run.status,
    poll_url=f"/itinerary-plan-runs/{run.run_id}?user={request.user}",
    progress_events=[
      ItineraryPlanRunEventResponse(**event)
      for event in run.progress_events
    ],
    created_at=run.created_at,
    updated_at=run.updated_at,
  )

@app.get("/itinerary-plan-runs/{run_id}", response_model=ItineraryPlanRunResponse)
def get_itinerary_plan_run_status(run_id: str, user: str = "local") -> ItineraryPlanRunResponse:
  try:
    with get_session() as session:
      run = get_itinerary_plan_run(session, user_slug=user, run_id=run_id)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  if run is None:
    raise HTTPException(status_code=404, detail="Itinerary planning run not found.")

  return ItineraryPlanRunResponse(
    run_id=run.run_id,
    original_prompt=run.original_prompt,
    model_name=run.model_name,
    save=run.save,
    status=run.status,
    progress_events=[
      ItineraryPlanRunEventResponse(**event)
      for event in run.progress_events
    ],
    error_message=run.error_message,
    plan_id=run.plan_id,
    trip_request_id=run.trip_request_id,
    created_at=run.created_at,
    updated_at=run.updated_at,
  )

@app.post("/itinerary-plans", response_model=ItineraryPlanCreateResponse)
def create_itinerary_plan(request: ItineraryPlanRequest) -> ItineraryPlanCreateResponse:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  client = get_ollama_client()

  try:
    with get_session() as session:
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
        prompt=request.prompt,
        user_slug=request.user,
        model=resolved_model,
        client=client,
        session=session,
        save=request.save,
        rag_retriever=rag_retriever,
      )
  except (OllamaError, TripExtractionError, ItineraryGenerationError) as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
  
  return ItineraryPlanCreateResponse(
    plan_id=result.saved.plan_id if result.saved else None,
    trip_request_id=result.saved.trip_request_id if result.saved else None,
    trip_request=result.trip_request.model_dump(mode="json"),
    active_context=result.active_context.model_dump(mode="json"),
    rag_context=result.rag_context.model_dump(mode="json") if result.rag_context else None,
    itinerary=result.itinerary.model_dump(mode="json"),
    itinerary_diagnostics=ItineraryDiagnosticsResponse(
      repair_attempted=result.itinerary_diagnostics.repair_attempted,
      repair_succeeded=result.itinerary_diagnostics.repair_succeeded,
      initial_validation_error=result.itinerary_diagnostics.initial_validation_error,
      quality_status=result.itinerary_diagnostics.quality_status,
      quality_issues=result.itinerary_diagnostics.quality_issues,
    ),
  )

@app.get("/itinerary-plans", response_model=ItineraryPlanListResponse)
def list_saved_itinerary_plans(user: str = "local") -> ItineraryPlanListResponse:
  try:
    with get_session() as session:
      plans = list_itinerary_plans(session, user_slug=user)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  return ItineraryPlanListResponse(
    plans=[
      ItineraryPlanSummaryResponse(
        plan_id=plan.plan_id,
        trip_request_id=plan.trip_request_id,
        original_prompt=plan.original_prompt,
        title=plan.title,
        destination=plan.destination,
        created_at=plan.created_at,
      )
      for plan in plans
    ],
  )

@app.get("/itinerary-plans/{plan_id}/summary", response_model=MobileItineraryPlanSummaryResponse)
def get_saved_itinerary_plan_summary(
    plan_id: str,
    user: str = "local",
) -> MobileItineraryPlanSummaryResponse:
  try:
    with get_session() as session:
      plan = get_itinerary_plan(session, user_slug=user, plan_id=plan_id)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  if plan is None:
    raise HTTPException(status_code=404, detail="Itinerary plan not found.")

  return _build_mobile_plan_summary(plan)

@app.get("/itinerary-plans/{plan_id}", response_model=StoredItineraryPlanResponse)
def get_saved_itinerary_plan(plan_id: str, user: str = "local") -> StoredItineraryPlanResponse:
  try:
    with get_session() as session:
      plan = get_itinerary_plan(session, user_slug=user, plan_id=plan_id)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
  
  if plan is None:
    raise HTTPException(status_code=404, detail="Itinerary plan not found.")
  
  return StoredItineraryPlanResponse(
    plan_id=plan.plan_id,
    trip_request_id=plan.trip_request_id,
    original_prompt=plan.original_prompt,
    trip_request=plan.trip_request,
    active_context=plan.active_context,
    itinerary=plan.itinerary,
    model_name=plan.model_name,
    rag_context=plan.rag_context,
    itinerary_diagnostics=plan.itinerary_diagnostics,
    created_at=plan.created_at,
  )
