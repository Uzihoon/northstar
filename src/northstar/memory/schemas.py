from pydantic import BaseModel, Field, field_validator

from northstar.agent.schemas import BudgetLevel, Pace

def _normalize_list(value: object) -> list[str]:
  if value is None or not isinstance(value, list):
    return []
  
  result: list[str] = []
  seen: set[str] = set()
  for item in value:
    if not isinstance(item, str):
      continue
    cleaned = " ".join(item.strip().lower().split())
    if cleaned and cleaned not in seen:
      result.append(cleaned)
      seen.add(cleaned)
  
  return result

class UserPreferenceProfile(BaseModel):
  pace: Pace | None = None
  budget_level: BudgetLevel | None = None
  interests: list[str] = Field(default_factory=list)
  food_preferences: list[str] = Field(default_factory=list)
  dislikes: list[str] = Field(default_factory=list)
  notes: list[str] = Field(default_factory=list)

  @field_validator("interests", "food_preferences", "dislikes", "notes", mode="before")
  @classmethod
  def normalize_lists(cls, value: object) -> list[str]:
    return _normalize_list(value)
  
class PreferenceUpdateCandidate(BaseModel):
  pace: Pace | None = None
  budget_level: BudgetLevel | None = None
  interests_to_add: list[str] = Field(default_factory=list)
  food_preferences_to_add: list[str] = Field(default_factory=list)
  dislikes_to_add: list[str] = Field(default_factory=list)
  notes_to_add: list[str] = Field(default_factory=list)
  evidence: list[str] = Field(default_factory=list)

  @field_validator(
    "interests_to_add",
    "food_preferences_to_add",
    "dislikes_to_add",
    "notes_to_add",
    "evidence",
    mode="before",
  )
  @classmethod
  def normalize_list(cls, value: object) -> list[str]:
    return _normalize_list(value)
