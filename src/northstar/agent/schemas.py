from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

class BudgetLevel(str, Enum):
  budget = "budget"
  midrange = "midrange"
  luxury = "luxury"

class Pace(str, Enum):
  relaxed = "relaxed"
  balanced = "balanced"
  fast = "fast"

class MissingInfoCode(str, Enum):
  exact_travel_dates = "exact_travel_dates"
  budget_level = "budget_level"
  accommodation_preferences = "accommodation_preferences"
  transportation_preferences = "transportation_preferences"
  activity_preferences = "activity_preferences"

FOOD_HINTS = (
  "food",
  "vegetarian",
  "vegan",
  "restaurant",
  "restaurants",
  "cuisine",
  "cuisines",
  "street food",
  "fine dining",
  "brunch",
  "coffee",
  "dessert",
  "sushi",
  "ramen",
)

class TripRequest(BaseModel):
  destination_city: str | None = Field(
    default=None,
    description="Destination city. Null if the user did not specify one."
  )
  country: str | None = Field(
    default=None,
    description=(
      "Destination country. It may be inferred when the city is widely and "
      "unambiguously associated with one country, such as Kyoto -> Japan."
    )
  )
  start_date: str | None = Field(
    default=None,
    description="Trip start date in YYYY-MM-DD format, or null if unknown."
  )
  end_date: str | None = Field(
    default=None,
    description="Trip end date in YYYY-MM-DD format, or null if unknown."
  )
  duration_days: int | None = Field(
    default=None,
    description="Trip duration in days if stated or strongly implied."
  )
  budget_level: BudgetLevel | None = Field(
    default=None,
    description="Normalized budget bucket."
  )
  pace: Pace | None = Field(
    default=None,
    description="Normalized trip pace."
  )
  interests: list[str] = Field(
    default_factory=list,
    description=(
      "Activities, attractions, neighborhoods, and vibes only."
      "Examples: cafes, bookstores, museums, nightlife, quiet neighborhoods."
    )
  )
  food_preferences: list[str] = Field(
    default_factory=list,
    description=(
      "Dietary preferences, cuisines, restaurant styles, and food-related interests."
      "Examples: vegetarian, vegan, sushi, ramen, street food, coffee."
    )
  )
  constraints: list[str] = Field(
    default_factory=list,
    description="Important trip constraints such as mobility limits or early flights."
  )
  missing_info: list[MissingInfoCode] = Field(
    default_factory=list,
    description=(
      "Only include stable codes for information that materially blocks a tailored first draft."
    )
  )

  @field_validator("destination_city", "country", mode="before")
  @classmethod
  def normalize_optional_text(cls, value: object) -> str | None:
    if value is None or not isinstance(value, str):
      return None
    
    cleaned = " ".join(value.strip().split())
    return cleaned or None
  
  @field_validator("interests", "food_preferences", "constraints", mode="before")
  @classmethod
  def normalize_string_lists(cls, value: object) -> list[str]:
    if value is None or not isinstance(value, list):
      return []
    
    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
      if not isinstance(item, str):
        continue

      cleaned = " ".join(item.strip().lower().split())
      if not cleaned or cleaned in seen:
        continue

      normalized.append(cleaned)
      seen.add(cleaned)

    return normalized
  
  @field_validator("missing_info", mode="before")
  @classmethod
  def normalize_missing_info(cls, value: object) -> list[str]:
    if value is None or not isinstance(value, list):
      return []
    
    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
      if isinstance(item, MissingInfoCode):
        code = item.value
      elif isinstance(item, str):
        code = item.strip().lower().replace(" ", "_")
      else:
        continue
    
      if code and code not in seen:
        normalized.append(code)
        seen.add(code)
    
    return normalized

