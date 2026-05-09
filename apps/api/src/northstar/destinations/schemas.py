from pydantic import BaseModel, Field


class DestinationRagConfig(BaseModel):
  namespace: str
  country: str
  city: str
  doc_types: list[str] = Field(default_factory=list)
  source_queries: list[str] = Field(default_factory=list)


class Destination(BaseModel):
  id: str
  city: str
  country: str
  country_slug: str
  city_slug: str
  title: str
  summary: str
  description: str
  vibes: list[str] = Field(default_factory=list)
  best_for: list[str] = Field(default_factory=list)
  avoid_if: list[str] = Field(default_factory=list)
  suggested_duration_days: list[int] = Field(default_factory=list)
  hero_image_url: str | None = None
  tags: list[str] = Field(default_factory=list)
  rag: DestinationRagConfig
