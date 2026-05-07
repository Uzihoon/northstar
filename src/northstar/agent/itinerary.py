import json
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
  def validate_transport_metadata(self) -> "TimelineItem":
    if self.type != TimelineItemType.transport:
      return self

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
- Every meal item should include cuisine, dietary_fit, and reservation_recommended.
- Every cafe item should include dietary_fit when food_preferences apply.
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
) -> ItineraryPlan:
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
      return ItineraryPlan.model_validate(payload)
    except ValidationError as exc:
      return repair_structured_itinerary(
        invalid_payload=payload,
        validation_error=exc,
        context=context,
        rag_context=rag_context,
        model=model,
        client=client,
      )
  except ValidationError as exc:
    raise ItineraryGenerationError(
      "Northstar could not validate the generated itinerary after repair."
    ) from exc
  except RuntimeError as exc:
    raise ItineraryGenerationError(
      f"Northstar could not parse the model's itinerary response. {exc}"
    ) from exc
