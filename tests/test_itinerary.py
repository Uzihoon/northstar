from northstar.agent.context import ActivePlanContext
from northstar.agent.itinerary import ItineraryPlan, generate_itinerary_plan
from northstar.rag.schemas import RagContext, RagSource

class CapturingFakeOllamaClient:
  def __init__(self) -> None:
    self.messages = []

  def structured_chat(self, *, messages, model, response_format):
    self.messages = messages

    return {
      "title": "A RAG-grounded Kyoto plan",
      "destination": "Kyoto, Japan",
      "duration_days": 2,
      "preferences_used": ["cafes"],
      "assumptions": [],
      "days": [],
    }

class FakeOllamaClient:
  def structured_chat(self, *, messages, model, response_format):
    return {
      "title": "A relaxed 2-day Kyoto cafe and bookstore trip",
      "destination": "Kyoto, Japan",
      "duration_days": 2,
      "preferences_used": ["relaxed pace", "cafes", "bookstores", "vegetarian"],
      "assumptions": ["Exact dates were not provided, so times are model estimates."],
      "days": [
        {
          "day_number": 1,
          "date": None,
          "theme": "Quiet neighborhoods and cafes",
          "timeline_items": [
            {
              "type": "place",
              "start_time": "09:30",
              "end_time": "11:00",
              "time_source": "model_estimate",
              "title": "Philosopher's Path",
              "description": "A calm morning walk.",
              "area": "Higashiyama",
              "preference_match": ["relaxed pace", "quiet vibes"],
              "source_notes": [],
              "place_category": "sightseeing",
              "indoor_outdoor": "outdoor",
            },
            {
              "type": "transport",
              "start_time": "11:00",
              "end_time": "11:25",
              "time_source": "model_estimate",
              "title": "Move to Gion",
              "description": "Travel from Higashiyama toward Gion.",
              "preference_match": [],
              "source_notes": ["Estimated without maps API."],
              "transport_mode": "bus",
              "from_location": "Philosopher's Path",
              "to_location": "Gion",
              "duration_minutes": 25,
            },
            {
              "type": "break_time",
              "start_time": "11:25",
              "end_time": "12:00",
              "time_source": "model_estimate",
              "title": "Slow buffer before lunch",
              "description": "A short break to keep the day relaxed.",
              "preference_match": ["relaxed pace"],
              "source_notes": [],
            },
          ],
        }
      ],
    }


def test_generate_itinerary_plan_returns_validated_plan() -> None:
  context = ActivePlanContext(
    destination_city="Kyoto",
    country="Japan",
    duration_days=2,
    pace="relaxed",
    interests=["cafes", "bookstores", "quiet vibes"],
    food_preferences=["vegetarian"],
  )

  plan = generate_itinerary_plan(
    context=context,
    model="qwen3.6:27b",
    client=FakeOllamaClient(),
  )

  assert isinstance(plan, ItineraryPlan)
  assert plan.destination == "Kyoto, Japan"
  assert plan.days[0].timeline_items[0].type == "place"
  assert plan.days[0].timeline_items[1].type == "transport"
  assert plan.days[0].timeline_items[1].duration_minutes == 25
  assert plan.days[0].timeline_items[2].type == "break_time"

def test_generate_itinerary_plan_includes_rag_context_in_prompt() -> None:
  client = CapturingFakeOllamaClient()
  context = ActivePlanContext(
    destination_city="Kyoto",
    country="Japan",
    duration_days=2,
    interests=["cafes"],
  )
  rag_context = RagContext(
    query="Kyoto Japan interests: cafes",
    notes=["Philosopher's Path is useful for quiet cafe breaks."],
    sources=[
      RagSource(
        chunk_id="chunk-1",
        source_path="rag_docs/japan/kyoto/cafes.md",
        score=0.91,
        metadata={"city": "Kyoto", "country": "Japan"},
      )
    ],
  )

  generate_itinerary_plan(
    context=context,
    model="qwen3.6:27b",
    client=client,
    rag_context=rag_context,
  )

  user_message = client.messages[1]["content"]

  assert "Philosopher's Path is useful for quiet cafe breaks." in user_message
  assert "rag_docs/japan/kyoto/cafes.md" in user_message
