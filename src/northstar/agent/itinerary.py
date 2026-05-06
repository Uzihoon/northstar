import json
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

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
- Use transport items when moving between areas or major stops.
- Use meal or cafe items for food and drink stops.
- Use place items for museums, sightseeing, neighborhoods, parks, shops, and attractions.
- Use time_source=model_estimate unless the context explicitly provides exact timing.
- Use break_time items for rest, downtime, buffer time, or recovery between activities.
- Mention user preferences in preferences_used and preference_match.
- If exact dates are missing, make reasonable timing assumptions and include them in assumptions.
""".strip()

def generate_itinerary_plan(
    *,
    context: ActivePlanContext,
    model: str,
    client: OllamaClient,
    rag_context: RagContext | None = None,
) -> ItineraryPlan:
  user_payload = {
    "active_context": context.model_dump(mode="json"),
    "rag_context": rag_context.model_dump(mode="json") if rag_context else None
  }

  try:
    payload = client.structured_chat(
      messages=[
        {"role": "system", "content": ITINERARY_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, indent=2)}
      ],
      model=model,
      response_format=ItineraryPlan.model_json_schema(),
    )
    return ItineraryPlan.model_validate(payload)
  except ValidationError as exc:
    raise ItineraryGenerationError(
      "Northstar could not validate the generated itinerary."
    ) from exc
  except RuntimeError as exc:
    raise ItineraryGenerationError(
      f"Northstar could not parse the model's itinerary response. {exc}"
    ) from exc