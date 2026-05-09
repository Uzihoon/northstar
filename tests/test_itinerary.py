from northstar.agent.context import ActivePlanContext
import pytest
from pydantic import ValidationError

from northstar.agent.itinerary import (
  ItineraryGenerationError,
  ItineraryPlan,
  RecommendationOption,
  TimelineItem,
  evaluate_itinerary_quality,
  generate_itinerary_plan,
)
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
              "title": "Slow buffer before the next stop",
              "description": "A short rest break to keep the day relaxed.",
              "preference_match": ["relaxed pace"],
              "source_notes": [],
            },
          ],
        }
      ],
    }

class RepairingFakeOllamaClient:
  def __init__(self) -> None:
    self.calls = 0
    self.messages = []

  def structured_chat(self, *, messages, model, response_format):
    self.calls += 1
    self.messages.append(messages)

    if self.calls == 1:
      return {
        "title": "A plan with malformed transport",
        "destination": "Kyoto, Japan",
        "duration_days": 2,
        "preferences_used": ["cafes"],
        "assumptions": [],
        "days": [
          {
            "day_number": 1,
            "theme": "Quiet Kyoto",
            "timeline_items": [
              {
                "type": "transport",
                "start_time": "10:00",
                "end_time": "10:20",
                "description": "Travel to Gion.",
              }
            ],
          }
        ],
      }

    return {
      "title": "A repaired Kyoto plan",
      "destination": "Kyoto, Japan",
      "duration_days": 2,
      "preferences_used": ["cafes"],
      "assumptions": [],
      "days": [
        {
          "day_number": 1,
          "theme": "Quiet Kyoto",
          "timeline_items": [
            {
              "type": "transport",
              "start_time": "10:00",
              "end_time": "10:20",
              "title": "Move to Gion",
              "description": "Travel to Gion.",
              "transport_mode": "bus",
              "from_location": "Philosopher's Path",
              "to_location": "Gion",
              "duration_minutes": 20,
            }
          ],
        }
      ],
    }

class TypeRepairingFakeOllamaClient:
  def __init__(self) -> None:
    self.calls = 0

  def structured_chat(self, *, messages, model, response_format):
    self.calls += 1

    if self.calls == 1:
      return {
        "title": "A plan with dinner typed as place",
        "destination": "Kyoto, Japan",
        "duration_days": 2,
        "preferences_used": ["vegetarian"],
        "assumptions": [],
        "days": [
          {
            "day_number": 1,
            "theme": "Quiet Kyoto",
            "timeline_items": [
              {
                "type": "place",
                "start_time": "18:00",
                "end_time": "19:30",
                "title": "Dinner in Gion",
                "description": "Enjoy a vegetarian dinner.",
                "place_category": "Restaurant",
                "indoor_outdoor": "Indoor",
              }
            ],
          }
        ],
      }

    return {
      "title": "A repaired Kyoto food plan",
      "destination": "Kyoto, Japan",
      "duration_days": 2,
      "preferences_used": ["vegetarian"],
      "assumptions": [],
      "days": [
        {
          "day_number": 1,
          "theme": "Quiet Kyoto",
          "timeline_items": [
            {
              "type": "meal",
              "start_time": "18:00",
              "end_time": "19:30",
              "title": "Dinner in Gion",
              "description": "Enjoy a vegetarian dinner.",
              "area": "Gion",
              "cuisine": "Japanese vegetarian",
              "dietary_fit": ["vegetarian"],
              "reservation_recommended": False,
            }
          ],
        }
      ],
    }

class MixedBookstoreCafeRepairingFakeOllamaClient:
  def __init__(self) -> None:
    self.calls = 0

  def structured_chat(self, *, messages, model, response_format):
    self.calls += 1

    if self.calls == 1:
      return {
        "title": "A plan with mixed bookstore cafe item",
        "destination": "Kyoto, Japan",
        "duration_days": 2,
        "preferences_used": ["bookstores", "cafes"],
        "assumptions": [],
        "days": [
          {
            "day_number": 1,
            "theme": "Downtown Kyoto",
            "timeline_items": [
              {
                "type": "place",
                "start_time": "15:00",
                "end_time": "16:30",
                "title": "Bookstore and Cafe Break",
                "description": "Browse books and enjoy a quiet coffee break.",
                "place_category": "bookstore and cafe",
                "indoor_outdoor": "indoor",
              }
            ],
          }
        ],
      }

    return {
      "title": "A repaired bookstore and cafe plan",
      "destination": "Kyoto, Japan",
      "duration_days": 2,
      "preferences_used": ["bookstores", "cafes"],
      "assumptions": [],
      "days": [
        {
          "day_number": 1,
          "theme": "Downtown Kyoto",
          "timeline_items": [
            {
              "type": "place",
              "start_time": "15:00",
              "end_time": "15:45",
              "title": "Bookstore Browsing",
              "description": "Browse a quiet bookstore.",
              "place_category": "bookstore",
              "indoor_outdoor": "indoor",
            },
            {
              "type": "cafe",
              "start_time": "15:45",
              "end_time": "16:30",
              "title": "Cafe Break",
              "description": "Enjoy a quiet coffee break.",
              "dietary_fit": ["coffee"],
              "reservation_recommended": False,
            },
          ],
        }
      ],
    }

class AlwaysInvalidFakeOllamaClient:
  def structured_chat(self, *, messages, model, response_format):
    return {
      "title": "Still invalid",
      "destination": "Kyoto, Japan",
      "duration_days": 2,
      "preferences_used": [],
      "assumptions": [],
      "days": [
        {
          "day_number": 1,
          "theme": "Invalid transport",
          "timeline_items": [
            {
              "type": "unknown",
              "start_time": "10:00",
              "end_time": "10:20",
              "title": "Move to Gion",
              "description": "Travel to Gion.",
            }
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

  assert isinstance(plan.itinerary, ItineraryPlan)
  assert plan.itinerary.destination == "Kyoto, Japan"
  assert plan.diagnostics.repair_attempted is False
  assert plan.itinerary.days[0].timeline_items[0].type == "place"
  assert plan.itinerary.days[0].timeline_items[1].type == "transport"
  assert plan.itinerary.days[0].timeline_items[1].duration_minutes == 25
  assert plan.itinerary.days[0].timeline_items[2].type == "break_time"

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


def test_itinerary_prompt_requires_source_safe_recommendation_options() -> None:
  from northstar.agent import itinerary

  assert "Do not invent real restaurant, cafe, hotel, or accommodation names." in itinerary.ITINERARY_SYSTEM_PROMPT
  assert "Use descriptive option labels" in itinerary.ITINERARY_SYSTEM_PROMPT
  assert "real venue names only when they appear in curated local notes" in itinerary.ITINERARY_SYSTEM_PROMPT
  assert "Keep source_notes populated" in itinerary.ITINERARY_SYSTEM_PROMPT


def test_transport_item_allows_missing_transport_metadata_for_soft_validation() -> None:
  item = TimelineItem(
    type="transport",
    start_time="10:30",
    end_time="10:45",
    title="Walk through Sannenzaka and Ninenzaka",
    description="A scenic walk through preserved streets.",
  )

  assert item.type == "transport"


def test_transport_item_accepts_complete_transport_metadata() -> None:
  item = TimelineItem(
    type="transport",
    start_time="10:30",
    end_time="10:45",
    title="Walk from Kiyomizu-dera to Sannenzaka",
    description="Move from the temple toward the historic streets.",
    transport_mode="walk",
    from_location="Kiyomizu-dera",
    to_location="Sannenzaka",
    duration_minutes=15,
  )

  assert item.transport_mode == "walk"
  assert item.duration_minutes == 15


def test_transport_item_allows_food_destination_intent() -> None:
  item = TimelineItem(
    type="transport",
    start_time="10:30",
    end_time="10:45",
    title="Travel to Cafe Area",
    description="Move from Higashiyama toward a cafe area.",
    transport_mode="walk",
    from_location="Higashiyama",
    to_location="Cafe Area",
    duration_minutes=15,
  )

  assert item.type == "transport"


def test_meal_item_allows_missing_food_metadata_for_soft_validation() -> None:
  item = TimelineItem(
    type="meal",
    start_time="18:00",
    end_time="19:30",
    title="Dinner in Gion",
    description="Enjoy dinner.",
  )

  assert item.type == "meal"


def test_meal_item_allows_missing_cuisine_when_dietary_metadata_exists() -> None:
  item = TimelineItem(
    type="meal",
    start_time="18:00",
    end_time="19:30",
    title="Dinner in Gion",
    description="Enjoy dinner.",
    dietary_fit=["vegetarian"],
    reservation_recommended=False,
  )

  assert item.cuisine is None
  assert item.dietary_fit == ["vegetarian"]


def test_meal_item_accepts_restaurant_options() -> None:
  item = TimelineItem(
    type="meal",
    start_time="18:00",
    end_time="19:30",
    title="Vegetarian dinner in Downtown Kyoto",
    description="Choose one of these relaxed vegetarian-friendly dinner options.",
    area="Downtown Kyoto",
    dietary_fit=["vegetarian"],
    reservation_recommended=True,
    options=[
      RecommendationOption(
        name="Quiet vegetarian izakaya",
        category="restaurant",
        area="Downtown Kyoto",
        why_it_fits="Vegetarian-friendly and calm enough for a relaxed evening.",
        estimated_cost="medium",
        reservation_recommended=True,
        tradeoffs=["May need booking ahead."],
      )
    ],
  )

  assert item.options[0].category == "restaurant"
  assert item.options[0].reservation_recommended is True


def test_itinerary_plan_accepts_accommodation_options() -> None:
  plan = ItineraryPlan(
    title="A relaxed Kyoto plan",
    destination="Kyoto, Japan",
    duration_days=2,
    preferences_used=["quiet neighborhoods"],
    assumptions=[],
    accommodation_options=[
      RecommendationOption(
        name="Quiet ryokan-style stay in Higashiyama",
        category="accommodation",
        area="Higashiyama",
        why_it_fits="Calm and walkable, with easy access to temples.",
        estimated_cost="medium-high",
        tradeoffs=["Less nightlife nearby."],
      )
    ],
    days=[],
  )

  assert plan.accommodation_options[0].category == "accommodation"


def test_cafe_item_allows_missing_reservation_recommendation_for_soft_validation() -> None:
  item = TimelineItem(
    type="cafe",
    start_time="10:45",
    end_time="11:30",
    title="Cafe Break",
    description="Coffee break.",
  )

  assert item.type == "cafe"


def test_place_item_allows_restaurant_or_meal_titles_for_soft_validation() -> None:
  item = TimelineItem(
    type="place",
    start_time="18:00",
    end_time="19:30",
    title="Dinner in Gion",
    description="Enjoy a vegetarian dinner.",
    place_category="Restaurant",
    indoor_outdoor="Indoor",
  )

  assert item.type == "place"


def test_break_time_item_allows_food_intent_for_soft_validation() -> None:
  item = TimelineItem(
    type="break_time",
    start_time="12:00",
    end_time="13:30",
    title="Lunch Break & Quiet Exploration",
    description="Enjoy a relaxed vegetarian lunch in the area.",
  )

  assert item.type == "break_time"


def test_free_time_item_allows_cafe_intent_for_soft_validation() -> None:
  item = TimelineItem(
    type="free_time",
    start_time="15:00",
    end_time="16:00",
    title="Coffee and browsing",
    description="A flexible coffee stop near downtown.",
  )

  assert item.type == "free_time"


def test_free_time_item_allows_incidental_dinner_reference() -> None:
  item = TimelineItem(
    type="free_time",
    start_time="17:30",
    end_time="18:30",
    title="Relax/Return to Accommodation",
    description="Rest at the hotel before dinner.",
  )

  assert item.type == "free_time"


def test_place_item_allows_missing_place_metadata_for_soft_validation() -> None:
  item = TimelineItem(
    type="place",
    start_time="09:30",
    end_time="11:00",
    title="Philosopher's Path",
    description="A calm morning walk.",
  )

  assert item.type == "place"


def test_evaluate_itinerary_quality_reports_soft_issues_without_rejecting_plan() -> None:
  plan = ItineraryPlan(
    title="A slightly messy Kyoto plan",
    destination="Kyoto, Japan",
    duration_days=1,
    days=[
      {
        "day_number": 1,
        "theme": "Downtown Kyoto",
        "timeline_items": [
          {
            "type": "place",
            "start_time": "15:00",
            "end_time": "16:30",
            "title": "Bookstore Browsing and Quiet Cafe Break",
            "description": "Browse books and enjoy a quiet coffee break.",
            "place_category": "bookstore and cafe",
            "indoor_outdoor": "indoor",
          },
          {
            "type": "meal",
            "start_time": "18:00",
            "end_time": "19:00",
            "title": "Dinner",
            "description": "Enjoy dinner.",
          },
        ],
      }
    ],
  )

  issues = evaluate_itinerary_quality(plan)

  assert {
    "severity": "warning",
    "code": "possible_misclassified_food_item",
    "path": "days.0.timeline_items.0",
    "message": "Item mentions food, cafe, coffee, or restaurant intent but is not typed as meal, cafe, or transport.",
  } in issues
  assert {
    "severity": "warning",
    "code": "missing_meal_metadata",
    "path": "days.0.timeline_items.1",
    "message": "Meal item is missing dietary_fit, reservation_recommended.",
  } in issues


def test_generate_itinerary_plan_repairs_invalid_structured_output() -> None:
  client = RepairingFakeOllamaClient()

  plan = generate_itinerary_plan(
    context=ActivePlanContext(
      destination_city="Kyoto",
      country="Japan",
      duration_days=2,
      interests=["cafes"],
    ),
    model="qwen3.6:27b",
    client=client,
  )

  assert client.calls == 2
  assert plan.itinerary.title == "A repaired Kyoto plan"
  assert plan.diagnostics.repair_attempted is True
  assert plan.diagnostics.repair_succeeded is True
  assert plan.diagnostics.initial_validation_error is not None
  assert plan.itinerary.days[0].timeline_items[0].duration_minutes == 20
  assert "Repair" in client.messages[1][0]["content"]


def test_generate_itinerary_plan_logs_misclassified_meal_as_quality_warning() -> None:
  client = TypeRepairingFakeOllamaClient()

  plan = generate_itinerary_plan(
    context=ActivePlanContext(
      destination_city="Kyoto",
      country="Japan",
      duration_days=2,
      food_preferences=["vegetarian"],
    ),
    model="qwen3.6:27b",
    client=client,
  )

  assert client.calls == 1
  assert plan.diagnostics.repair_attempted is False
  assert plan.diagnostics.quality_status == "warning"
  assert plan.diagnostics.quality_issues[0]["code"] == "possible_misclassified_food_item"
  assert plan.itinerary.days[0].timeline_items[0].type == "place"


def test_generate_itinerary_plan_logs_mixed_bookstore_and_cafe_item_as_quality_warning() -> None:
  client = MixedBookstoreCafeRepairingFakeOllamaClient()

  plan = generate_itinerary_plan(
    context=ActivePlanContext(
      destination_city="Kyoto",
      country="Japan",
      duration_days=2,
      interests=["bookstores", "cafes"],
    ),
    model="qwen3.6:27b",
    client=client,
  )

  items = plan.itinerary.days[0].timeline_items

  assert client.calls == 1
  assert plan.diagnostics.repair_attempted is False
  assert plan.diagnostics.quality_status == "warning"
  assert plan.diagnostics.quality_issues[0]["code"] == "possible_misclassified_food_item"
  assert [item.type for item in items] == ["place"]
  assert items[0].title == "Bookstore and Cafe Break"


def test_generate_itinerary_plan_raises_when_repair_fails() -> None:
  with pytest.raises(ItineraryGenerationError, match="days.0.timeline_items.0"):
    generate_itinerary_plan(
      context=ActivePlanContext(
        destination_city="Kyoto",
        country="Japan",
        duration_days=2,
      ),
      model="qwen3.6:27b",
      client=AlwaysInvalidFakeOllamaClient(),
    )
