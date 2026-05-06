from collections.abc import Callable

from sqlalchemy.orm import Session

from northstar.agent.context import ActivePlanContext
from northstar.ollama_client import OllamaClient
from northstar.rag.schemas import RagContext, RagSource
from northstar.rag.store import RagSearchResult, search_rag_chunks
from northstar.rag.metadata import normalize_slug

SearchRagChunksFn = Callable[..., list[RagSearchResult]]

def build_rag_query(context: ActivePlanContext) -> str:
  parts: list[str] = []

  if context.destination_city:
    parts.append(context.destination_city)

  if context.country:
    parts.append(context.country)

  if context.pace:
    parts.append(f"{context.pace.value} travel pace")

  if context.interests:
    parts.append("interests: " + ", ".join(context.interests))

  if context.food_preferences:
    parts.append("food preferences: " + ", ".join(context.food_preferences))

  if context.constraints:
    parts.append("constraints: " + ", ".join(context.constraints))

  return " | ".join(parts) or "travel planning notes"

def retrieve_travel_context(
    *,
    session: Session,
    context: ActivePlanContext,
    client: OllamaClient,
    embedding_model: str,
    embedding_dimensions: int,
    limit: int = 3,
    search_fn: SearchRagChunksFn = search_rag_chunks,
) -> RagContext:
  query = build_rag_query(context)
  country = normalize_slug(context.country)
  city = normalize_slug(context.destination_city)

  results = search_fn(
    session=session,
    query=query,
    client=client,
    embedding_model=embedding_model,
    embedding_dimensions=embedding_dimensions,
    limit=limit,
    country=country,
    city=city,
  )

  if not results and (country or city):
    results = search_fn(
      session=session,
      query=query,
      client=client,
      embedding_model=embedding_model,
      embedding_dimensions=embedding_dimensions,
      limit=limit,
    )

  return RagContext(
    query=query,
    notes=[result.text for result in results],
    sources=[
      RagSource(
        chunk_id=result.chunk_id,
        source_path=result.source_path,
        score=result.score,
        metadata=result.metadata,
      )
      for result in results
    ]
  )
