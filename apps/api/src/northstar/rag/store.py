from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from northstar.ollama_client import OllamaClient
from northstar.rag.chunker import chunk_markdown
from northstar.rag.models import RagChunkModel


class EmbeddingDimensionError(RuntimeError):
  pass


@dataclass(frozen=True)
class RagSearchResult:
  chunk_id: str
  source_path: str
  text: str
  metadata: dict[str, object]
  score: float


def validate_embedding_dimensions(
    *,
    embedding: list[float],
    expected_dimensions: int,
    model: str,
) -> None:
  actual_dimensions = len(embedding)

  if actual_dimensions != expected_dimensions:
    raise EmbeddingDimensionError(
      f"Embedding model {model!r} returned {actual_dimensions} dimensions, "
      f"but Northstar expected {expected_dimensions}. "
      "If you changed embedding models, re-check the vector column dimension "
      "and re-ingest RAG documents."
    )


def ingest_markdown_document(
    *,
    session: Session,
    path: Path,
    metadata: dict[str, object],
    client: OllamaClient,
    embedding_model: str,
    embedding_dimensions: int,
) -> int:
  text = path.read_text()
  chunks = chunk_markdown(text)

  for chunk in chunks:
    embedding = client.embed(text=chunk.text, model=embedding_model)
    validate_embedding_dimensions(
      embedding=embedding,
      expected_dimensions=embedding_dimensions,
      model=embedding_model,
    )

    session.add(
      RagChunkModel(
        source_path=str(path),
        chunk_index=chunk.index,
        text=chunk.text,
        chunk_metadata=metadata,
        embedding=embedding,
      )
    )

  session.commit()
  return len(chunks)


def delete_rag_chunks_for_source_path(*, session: Session, path: Path) -> int:
  result = session.execute(
    delete(RagChunkModel).where(RagChunkModel.source_path == str(path))
  )
  return int(result.rowcount or 0)


def replace_markdown_document(
    *,
    session: Session,
    path: Path,
    metadata: dict[str, object],
    client: OllamaClient,
    embedding_model: str,
    embedding_dimensions: int,
) -> int:
  delete_rag_chunks_for_source_path(session=session, path=path)
  return ingest_markdown_document(
    session=session,
    path=path,
    metadata=metadata,
    client=client,
    embedding_model=embedding_model,
    embedding_dimensions=embedding_dimensions,
  )


def search_rag_chunks(
    *,
    session: Session,
    query: str,
    client: OllamaClient,
    embedding_model: str,
    embedding_dimensions: int,
    limit: int = 5,
    country: str | None = None,
    city: str | None = None,
) -> list[RagSearchResult]:
  query_embedding = client.embed(text=query, model=embedding_model)
  validate_embedding_dimensions(
    embedding=query_embedding,
    expected_dimensions=embedding_dimensions,
    model=embedding_model,
  )

  distance = RagChunkModel.embedding.cosine_distance(query_embedding)
  statement = select(RagChunkModel, distance.label("distance"))

  if country:
    statement = statement.where(RagChunkModel.chunk_metadata["country"].as_string() == country)

  if city:
    statement = statement.where(RagChunkModel.chunk_metadata["city"].as_string() == city)

  rows = session.execute(
    statement.order_by(distance).limit(limit)
  ).all()

  return [
    RagSearchResult(
      chunk_id=row.id,
      source_path=row.source_path,
      text=row.text,
      metadata=row.chunk_metadata,
      score=1.0 - float(distance_value),
    )
    for row, distance_value in rows
  ]
