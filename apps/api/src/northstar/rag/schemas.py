from pydantic import BaseModel, Field

class RagSource(BaseModel):
  chunk_id: str
  source_path: str
  score: float
  metadata: dict[str, object] = Field(default_factory=dict)

class RagContext(BaseModel):
  query: str
  notes: list[str] = Field(default_factory=list)
  sources: list[RagSource] = Field(default_factory=list)