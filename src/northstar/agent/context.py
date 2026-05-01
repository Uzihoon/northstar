from pydantic import BaseModel, Field

from northstar.agent.schemas import BudgetLevel, Pace, TripRequest
from northstar.memory.schemas import UserPreferenceProfile


class ActivePlanContext(BaseModel):
  destination_city: str | None = None
  country: str | None = None
  start_date: str | None = None
  end_date: str | None = None
  duration_days: int | None = None
  pace: Pace | None = None
  budget_level: BudgetLevel | None = None
  interests: list[str] = Field(default_factory=list)
  food_preferences: list[str] = Field(default_factory=list)
  constraints: list[str] = Field(default_factory=list)
  missing_info: list[str] = Field(default_factory=list)
  profile_preferences_used: list[str] = Field(default_factory=list)
  trip_overrides_used: list[str] = Field(default_factory=list)


def _merge_unique(*lists: list[str]) -> list[str]:
  merged: list[str] = []
  seen: set[str] = set()

  for values in lists:
    for value in values:
      if value not in seen:
        merged.append(value)
        seen.add(value)

  return merged


def build_active_plan_context(
    *,
    profile: UserPreferenceProfile,
    trip_request: TripRequest,
) -> ActivePlanContext:
  profile_used: list[str] = []
  trip_overrides: list[str] = []

  pace = trip_request.pace or profile.pace
  if trip_request.pace is not None:
    trip_overrides.append("pace")
  elif profile.pace is not None:
    profile_used.append("pace")

  budget_level = trip_request.budget_level or profile.budget_level
  if trip_request.budget_level is not None:
    trip_overrides.append("budget_level")
  elif profile.budget_level is not None:
    profile_used.append("budget_level")

  interests = _merge_unique(profile.interests, trip_request.interests)
  if profile.interests:
    profile_used.append("interests")
  if trip_request.interests:
    trip_overrides.append("interests")

  food_preferences = _merge_unique(profile.food_preferences, trip_request.food_preferences)
  if profile.food_preferences:
    profile_used.append("food_preferences")
  if trip_request.food_preferences:
    trip_overrides.append("food_preferences")

  return ActivePlanContext(
    destination_city=trip_request.destination_city,
    country=trip_request.country,
    start_date=trip_request.start_date,
    end_date=trip_request.end_date,
    duration_days=trip_request.duration_days,
    pace=pace,
    budget_level=budget_level,
    interests=interests,
    food_preferences=food_preferences,
    constraints=trip_request.constraints,
    missing_info=[item.value for item in trip_request.missing_info],
    profile_preferences_used=profile_used,
    trip_overrides_used=trip_overrides,
  )
