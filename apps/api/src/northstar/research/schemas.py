from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
  return datetime.now(timezone.utc)


class ResearchTheme(str, Enum):
  overview = "overview"
  neighborhoods = "neighborhoods"
  cafes = "cafes"
  restaurants = "restaurants"
  sightseeing = "sightseeing"
  transport = "transport"
  accommodation = "accommodation"


class TrustRating(str, Enum):
  high = "high"
  medium = "medium"
  low = "low"
  blocked = "blocked"


class PriceLevel(str, Enum):
  free = "free"
  budget = "budget"
  moderate = "moderate"
  expensive = "expensive"
  luxury = "luxury"
  varies = "varies"


class CandidateCategory(str, Enum):
  cafe = "cafe"
  restaurant = "restaurant"
  accommodation = "accommodation"
  attraction = "attraction"
  shop = "shop"
  other = "other"


class SourceReference(BaseModel):
  title: str
  url: str
  fetched_at: datetime | None = None
  content_hash: str | None = None
  trust_hint: TrustRating | None = None


class ResearchTarget(BaseModel):
  country: str
  city: str
  themes: list[ResearchTheme] = Field(default_factory=lambda: list(ResearchTheme))
  trusted_urls: list[str] = Field(default_factory=list)


class StableNoteDraft(BaseModel):
  theme: ResearchTheme
  title: str
  markdown: str
  trust_rating: TrustRating
  sources: list[SourceReference] = Field(default_factory=list)


class CandidateOption(BaseModel):
  name: str
  category: CandidateCategory | str
  country: str
  city: str
  area: str | None = None
  description: str
  price_level: PriceLevel = PriceLevel.varies
  trust_rating: TrustRating
  source_urls: list[str] = Field(default_factory=list)
  last_checked_at: datetime = Field(default_factory=utc_now)
  metadata: dict[str, object] = Field(default_factory=dict)


class BlockedResearchItem(BaseModel):
  title: str
  reason: str
  source_urls: list[str] = Field(default_factory=list)


class ResearchDraft(BaseModel):
  target: ResearchTarget
  stable_notes: list[StableNoteDraft] = Field(default_factory=list)
  candidates: list[CandidateOption] = Field(default_factory=list)
  blocked_items: list[BlockedResearchItem] = Field(default_factory=list)


class ResearchValidationIssue(BaseModel):
  code: str
  path: str
  message: str


class ResearchValidationReport(BaseModel):
  passed: bool
  issues: list[ResearchValidationIssue] = Field(default_factory=list)
