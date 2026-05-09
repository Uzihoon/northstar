import json
import logging
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from northstar.agent.context import ActivePlanContext
from northstar.ollama_client import OllamaClient
from northstar.rag.schemas import RagContext

logger = logging.getLogger(__name__)

class ItineraryGenerationError(RuntimeError):
  """Raised when itinerary generation fails."""

class TimelineItemType(str, Enum):
  place = "place"
  meal = "meal"
  cafe = "cafe"
  transport = "transport"
  break_time = "break_time"
  free_time = "free_time"
  note = "note"

class TimeSource(str, Enum):
  model_estimate = "model_estimate"
  user_provided = "user_provided"
  maps_api = "maps_api"

class RecommendationOption(BaseModel):
  name: str
  category: str
  area: str | None = None
  why_it_fits: str
  estimated_cost: str | None = None
  reservation_recommended: bool | None = None
  tradeoffs: list[str] = Field(default_factory=list)
  source_notes: list[str] = Field(default_factory=list)

class TimelineItem(BaseModel):
  type: TimelineItemType
  start_time: str = Field(description="Start time in HH:MM 24-hour format.")
  end_time: str = Field(description="End time in HH:MM 24-hour format.")
  time_source: TimeSource = TimeSource.model_estimate

  title: str
  description: str
  area: str | None = None
  preference_match: list[str] = Field(default_factory=list)
  source_notes: list[str] = Field(default_factory=list)

  transport_mode: str | None = None
  from_location: str | None = None
  to_location: str | None = None
  duration_minutes: int | None = None

  cuisine: str | None = None
  dietary_fit: list[str] = Field(default_factory=list)
  reservation_recommended: bool | None = None

  place_category: str | None = None
  indoor_outdoor: str | None = None
  estimated_cost: str | None = None
  options: list[RecommendationOption] = Field(default_factory=list)

class ItineraryDay(BaseModel):
  day_number: int
  date: str | None = None
  theme: str
  timeline_items: list[TimelineItem] = Field(default_factory=list)

class ItineraryPlan(BaseModel):
  title: str
  destination: str
  duration_days: int
  preferences_used: list[str] = Field(default_factory=list)
  assumptions: list[str] = Field(default_factory=list)
  accommodation_options: list[RecommendationOption] = Field(default_factory=list)
  days: list[ItineraryDay] = Field(default_factory=list)

@dataclass(frozen=True)
class ItineraryGenerationDiagnostics:
  repair_attempted: bool = False
  repair_succeeded: bool = False
  initial_validation_error: str | None = None
  quality_status: str = "ok"
  quality_issues: list[dict[str, str]] = field(default_factory=list)

@dataclass(frozen=True)
class ItineraryGenerationResult:
  itinerary: ItineraryPlan
  diagnostics: ItineraryGenerationDiagnostics

def _format_validation_error(exc: ValidationError) -> str:
  first_error = exc.errors()[0]
  location = ".".join(str(part) for part in first_error.get("loc", []))
  message = first_error.get("msg", "Validation failed.")
  offending_input = first_error.get("input")

  if isinstance(offending_input, dict):
    item_type = offending_input.get("type")
    title = offending_input.get("title")

    if item_type or title:
      return (
        f"{location}: {message} "
        f"Offending item: type={item_type!r}, title={title!r}."
      )

  if location:
    return f"{location}: {message}"

  return str(message)

def _quality_issue(
    *,
    code: str,
    path: str,
    message: str,
    severity: str = "warning",
) -> dict[str, str]:
  return {
    "severity": severity,
    "code": code,
    "path": path,
    "message": message,
  }

def _has_food_intent(item: TimelineItem) -> bool:
  title = item.title.lower()
  description = item.description.lower()
  place_category = (item.place_category or "").lower()
  food_words = [
    "breakfast",
    "brunch",
    "lunch",
    "dinner",
    "cafe",
    "coffee",
    "restaurant",
    "vegetarian",
  ]
  food_description_phrases = [
    "breakfast at",
    "brunch at",
    "lunch break",
    "lunch at",
    "lunch in",
    "dinner at",
    "dinner in",
    "enjoy dinner",
    "coffee break",
    "coffee stop",
    "cafe break",
    "café break",
    "cafe stop",
    "café stop",
    "restaurant",
    "vegetarian lunch",
    "vegetarian dinner",
  ]

  return (
    any(word in title or word in place_category for word in food_words)
    or any(phrase in description for phrase in food_description_phrases)
  )

def evaluate_itinerary_quality(plan: ItineraryPlan) -> list[dict[str, str]]:
  issues: list[dict[str, str]] = []

  for day_index, day in enumerate(plan.days):
    for item_index, item in enumerate(day.timeline_items):
      path = f"days.{day_index}.timeline_items.{item_index}"

      if _has_food_intent(item) and item.type not in {
        TimelineItemType.meal,
        TimelineItemType.cafe,
        TimelineItemType.transport,
      }:
        issues.append(
          _quality_issue(
            code="possible_misclassified_food_item",
            path=path,
            message=(
              "Item mentions food, cafe, coffee, or restaurant intent but is not "
              "typed as meal, cafe, or transport."
            ),
          )
        )

      if item.type == TimelineItemType.transport:
        missing_fields: list[str] = []
        if not item.transport_mode:
          missing_fields.append("transport_mode")
        if not item.from_location:
          missing_fields.append("from_location")
        if not item.to_location:
          missing_fields.append("to_location")
        if item.duration_minutes is None:
          missing_fields.append("duration_minutes")

        if missing_fields:
          issues.append(
            _quality_issue(
              code="missing_transport_metadata",
              path=path,
              message=(
                "Transport item is missing "
                + ", ".join(missing_fields)
                + "."
              ),
            )
          )

      if item.type == TimelineItemType.meal:
        missing_fields = []
        if not item.dietary_fit:
          missing_fields.append("dietary_fit")
        if item.reservation_recommended is None:
          missing_fields.append("reservation_recommended")

        if missing_fields:
          issues.append(
            _quality_issue(
              code="missing_meal_metadata",
              path=path,
              message=(
                "Meal item is missing "
                + ", ".join(missing_fields)
                + "."
              ),
            )
          )

      if item.type == TimelineItemType.cafe and item.reservation_recommended is None:
        issues.append(
          _quality_issue(
            code="missing_cafe_metadata",
            path=path,
            message="Cafe item is missing reservation_recommended.",
          )
        )

      if item.type == TimelineItemType.place:
        missing_fields = []
        if not item.place_category:
          missing_fields.append("place_category")
        if not item.indoor_outdoor:
          missing_fields.append("indoor_outdoor")

        if missing_fields:
          issues.append(
            _quality_issue(
              code="missing_place_metadata",
              path=path,
              message=(
                "Place item is missing "
                + ", ".join(missing_fields)
                + "."
              ),
            )
          )

      if not item.area and item.type in {
        TimelineItemType.place,
        TimelineItemType.meal,
        TimelineItemType.cafe,
      }:
        issues.append(
          _quality_issue(
            code="missing_area",
            path=path,
            message="Item is missing area.",
          )
        )

  return issues

def _build_diagnostics(
    *,
    repair_attempted: bool = False,
    repair_succeeded: bool = False,
    initial_validation_error: str | None = None,
    itinerary: ItineraryPlan,
) -> ItineraryGenerationDiagnostics:
  quality_issues = evaluate_itinerary_quality(itinerary)

  if quality_issues:
    logger.warning(
      "Generated itinerary has %s quality warning(s): %s",
      len(quality_issues),
      quality_issues,
    )

  return ItineraryGenerationDiagnostics(
    repair_attempted=repair_attempted,
    repair_succeeded=repair_succeeded,
    initial_validation_error=initial_validation_error,
    quality_status="warning" if quality_issues else "ok",
    quality_issues=quality_issues,
  )

ITINERARY_SYSTEM_PROMPT = """
You create structured travel itineraries.

Rules:
- If curated local notes are provided, use them when relevant.
- Do not invent that a curated source said something unless it appears in the notes.
- When a timeline item uses curated local notes, mention that briefly in source_notes.
- Return only JSON matching the schema.
- Build a realistic day-by-day timeline.
- Every timeline item must include start_time and end_time in HH:MM 24-hour format.
- Every timeline item should include area when the location or neighborhood is known.
- Every timeline item should include at least one preference_match when it supports a user preference.
- Use transport items only for movement between two locations or areas.
- Do not label scenic walking or neighborhood exploration as transport unless the main purpose is moving from one location to another.
- Every transport item must include transport_mode, from_location, to_location, and duration_minutes.
- Use meal or cafe items for food and drink stops.
- Every meal item must include dietary_fit and reservation_recommended.
- Every meal item should include cuisine when known.
- Meal items should include 2-3 restaurant options when useful. Put those choices in options.
- Restaurant options should include name, category="restaurant", area, why_it_fits, estimated_cost, reservation_recommended, and tradeoffs when known.
- Every cafe item should include dietary_fit when food_preferences apply.
- Cafe items may include options, but this is less important than restaurant meal options.
- Add 2-3 accommodation options at the itinerary top level when possible.
- Accommodation options should use category="accommodation" and include area, why_it_fits, estimated_cost, and tradeoffs when known.
- Do not invent real restaurant, cafe, hotel, or accommodation names.
- Use descriptive option labels unless the real venue names appear in curated local notes.
- Use real venue names only when they appear in curated local notes, and cite that evidence in source_notes.
- Keep source_notes populated for any recommendation option that uses a real source-backed venue name.
- Prefer type=meal or type=cafe for food, coffee, restaurant, lunch, or dinner stops.
- Transport items may mention food/cafe locations when the item is movement to that location.
- Avoid using break_time, free_time, note, or place for primary meals, cafes, coffee stops, or restaurants.
- If an activity combines browsing/shopping with food or coffee, choose the dominant activity type and keep the title clear.
- Use place items for museums, sightseeing, neighborhoods, parks, shops, and attractions.
- Every place item should include place_category and indoor_outdoor.
- Use place or free_time for scenic walks, browsing, wandering, or neighborhood exploration.
- Use time_source=model_estimate unless the context explicitly provides exact timing.
- Use break_time items for rest, downtime, buffer time, or recovery between activities.
- Mention user preferences in preferences_used and preference_match.
- If exact dates are missing, make reasonable timing assumptions and include them in assumptions.
""".strip()

ITINERARY_REPAIR_SYSTEM_PROMPT = """
Repair structured itinerary JSON.

Rules:
- Return only JSON matching the schema.
- Preserve the original itinerary intent, destination, timing, and user preferences.
- Fix only schema or validation problems.
- Do not add new facts unless required to satisfy validation.
- For transport items, include transport_mode, from_location, to_location, and duration_minutes.
- For meal items, include dietary_fit and reservation_recommended. Include cuisine when known.
- Preserve or add meal options when they are already present or easy to infer from the original payload.
- For cafe items, include reservation_recommended.
- Preserve accommodation_options when present.
- Do not invent real restaurant, cafe, hotel, or accommodation names during repair.
- Use descriptive option labels unless real venue names appear in curated local notes.
- Keep source_notes populated for source-backed real venue names.
- Prefer type=meal or type=cafe for primary food, coffee, restaurant, lunch, or dinner stops.
- Transport items may mention food/cafe locations when the item is movement to that location.
- Avoid using break_time, free_time, note, or place for primary meals, cafes, coffee stops, or restaurants.
- For place items, include place_category and indoor_outdoor.
""".strip()

def _build_itinerary_user_payload(
    *,
    context: ActivePlanContext,
    rag_context: RagContext | None,
) -> dict[str, object]:
  return {
    "active_context": context.model_dump(mode="json"),
    "rag_context": rag_context.model_dump(mode="json") if rag_context else None
  }

def repair_structured_itinerary(
    *,
    invalid_payload: dict[str, object],
    validation_error: ValidationError,
    context: ActivePlanContext,
    rag_context: RagContext | None,
    model: str,
    client: OllamaClient,
) -> ItineraryPlan:
  repair_payload = {
    "validation_error": str(validation_error),
    "original_payload": invalid_payload,
    "generation_context": _build_itinerary_user_payload(
      context=context,
      rag_context=rag_context,
    ),
  }

  repaired_payload = client.structured_chat(
    messages=[
      {"role": "system", "content": ITINERARY_REPAIR_SYSTEM_PROMPT},
      {"role": "user", "content": json.dumps(repair_payload, indent=2)}
    ],
    model=model,
    response_format=ItineraryPlan.model_json_schema(),
  )

  return ItineraryPlan.model_validate(repaired_payload)

def generate_itinerary_plan(
    *,
    context: ActivePlanContext,
    model: str,
    client: OllamaClient,
    rag_context: RagContext | None = None,
) -> ItineraryGenerationResult:
  user_payload = _build_itinerary_user_payload(
    context=context,
    rag_context=rag_context,
  )

  try:
    payload = client.structured_chat(
      messages=[
        {"role": "system", "content": ITINERARY_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, indent=2)}
      ],
      model=model,
      response_format=ItineraryPlan.model_json_schema(),
    )
    try:
      itinerary = ItineraryPlan.model_validate(payload)
      return ItineraryGenerationResult(
        itinerary=itinerary,
        diagnostics=_build_diagnostics(itinerary=itinerary),
      )
    except ValidationError as exc:
      initial_validation_error = _format_validation_error(exc)
      itinerary = repair_structured_itinerary(
        invalid_payload=payload,
        validation_error=exc,
        context=context,
        rag_context=rag_context,
        model=model,
        client=client,
      )
      return ItineraryGenerationResult(
        itinerary=itinerary,
        diagnostics=_build_diagnostics(
          repair_attempted=True,
          repair_succeeded=True,
          initial_validation_error=initial_validation_error,
          itinerary=itinerary,
        ),
      )
  except ValidationError as exc:
    raise ItineraryGenerationError(
      "Northstar could not validate the generated itinerary after repair. "
      f"{_format_validation_error(exc)}"
    ) from exc
  except RuntimeError as exc:
    raise ItineraryGenerationError(
      f"Northstar could not parse the model's itinerary response. {exc}"
    ) from exc
