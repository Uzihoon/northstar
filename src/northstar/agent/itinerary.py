import json
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field, ValidationError, model_validator

from northstar.agent.context import ActivePlanContext
from northstar.ollama_client import OllamaClient
from northstar.rag.schemas import RagContext

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

  @model_validator(mode="after")
  def validate_type_specific_metadata(self) -> "TimelineItem":
    title = self.title.lower()
    description = self.description.lower()
    place_category = (self.place_category or "").lower()
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
    has_food_intent = (
      any(word in title or word in place_category for word in food_words)
      or any(phrase in description for phrase in food_description_phrases)
    )

    if has_food_intent and self.type not in {
      TimelineItemType.meal,
      TimelineItemType.cafe,
      TimelineItemType.transport,
    }:
      raise ValueError(
        "Food, cafe, coffee, or restaurant timeline items must use type=meal or type=cafe "
        "unless the item is transport to that location."
      )

    if self.type == TimelineItemType.transport:
      missing_fields: list[str] = []
      if not self.transport_mode:
        missing_fields.append("transport_mode")
      if not self.from_location:
        missing_fields.append("from_location")
      if not self.to_location:
        missing_fields.append("to_location")
      if self.duration_minutes is None:
        missing_fields.append("duration_minutes")

      if missing_fields:
        raise ValueError(
          "Transport timeline items must include "
          + ", ".join(missing_fields)
          + "."
        )

    if self.type == TimelineItemType.meal:
      missing_fields = []
      if not self.dietary_fit:
        missing_fields.append("dietary_fit")
      if self.reservation_recommended is None:
        missing_fields.append("reservation_recommended")

      if missing_fields:
        raise ValueError(
          "Meal timeline items must include "
          + ", ".join(missing_fields)
          + "."
        )

    if self.type == TimelineItemType.cafe:
      missing_fields = []
      if self.reservation_recommended is None:
        missing_fields.append("reservation_recommended")

      if missing_fields:
        raise ValueError(
          "Cafe timeline items must include "
          + ", ".join(missing_fields)
          + "."
        )

    if self.type == TimelineItemType.place:
      missing_fields = []
      if not self.place_category:
        missing_fields.append("place_category")
      if not self.indoor_outdoor:
        missing_fields.append("indoor_outdoor")

      if missing_fields:
        raise ValueError(
          "Place timeline items must include "
          + ", ".join(missing_fields)
          + "."
        )

    return self

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
  days: list[ItineraryDay] = Field(default_factory=list)

@dataclass(frozen=True)
class ItineraryGenerationDiagnostics:
  repair_attempted: bool = False
  repair_succeeded: bool = False
  initial_validation_error: str | None = None

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
- Every cafe item should include dietary_fit when food_preferences apply.
- Food, cafe, coffee, restaurant, lunch, or dinner items must use type=meal or type=cafe.
- Transport items may mention food/cafe locations only when the item is movement to that location.
- Do not use break_time, free_time, note, or place for meals, cafes, coffee stops, or restaurants.
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
- For cafe items, include reservation_recommended.
- Food, cafe, coffee, restaurant, lunch, or dinner items must use type=meal or type=cafe.
- Transport items may mention food/cafe locations only when the item is movement to that location.
- Do not use break_time, free_time, note, or place for meals, cafes, coffee stops, or restaurants.
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
        diagnostics=ItineraryGenerationDiagnostics(),
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
        diagnostics=ItineraryGenerationDiagnostics(
          repair_attempted=True,
          repair_succeeded=True,
          initial_validation_error=initial_validation_error,
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
