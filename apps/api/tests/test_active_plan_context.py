from northstar.agent.context import build_active_plan_context
from northstar.agent.schemas import TripRequest
from northstar.memory.schemas import UserPreferenceProfile


def test_build_active_plan_context_uses_profile_defaults_and_trip_specific_values() -> None:
  profile = UserPreferenceProfile(
    pace="relaxed",
    budget_level="midrange",
    interests=["cafes", "bookstores"],
    food_preferences=["vegetarian"],
  )
  trip_request = TripRequest(
    destination_city="Kyoto",
    country="Japan",
    duration_days=2,
    interests=["quiet vibes", "cafes"],
    food_preferences=["ramen"],
  )

  context = build_active_plan_context(profile=profile, trip_request=trip_request)

  assert context.destination_city == "Kyoto"
  assert context.country == "Japan"
  assert context.pace == "relaxed"
  assert context.budget_level == "midrange"
  assert context.interests == ["cafes", "bookstores", "quiet vibes"]
  assert context.food_preferences == ["vegetarian", "ramen"]
  assert context.profile_preferences_used == [
    "pace",
    "budget_level",
    "interests",
    "food_preferences",
  ]
  assert context.trip_overrides_used == ["interests", "food_preferences"]


def test_build_active_plan_context_trip_scalars_override_profile_scalars() -> None:
  profile = UserPreferenceProfile(pace="relaxed", budget_level="budget")
  trip_request = TripRequest(pace="fast", budget_level="luxury")

  context = build_active_plan_context(profile=profile, trip_request=trip_request)

  assert context.pace == "fast"
  assert context.budget_level == "luxury"
  assert context.profile_preferences_used == []
  assert context.trip_overrides_used == ["pace", "budget_level"]
