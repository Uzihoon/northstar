from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.rag.models import RagChunkModel
from northstar.rag.store import (
  EmbeddingDimensionError,
  replace_markdown_document,
  validate_embedding_dimensions,
)


class FakeEmbeddingClient:
  def embed(self, *, text: str, model: str) -> list[float]:
    return [0.1] * 1024


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


def test_validate_embedding_dimensions_accepts_expected_size() -> None:
  validate_embedding_dimensions(
    embedding=[0.1, 0.2, 0.3],
    expected_dimensions=3,
    model="test-embedding",
  )


def test_validate_embedding_dimensions_rejects_wrong_size() -> None:
  with pytest.raises(EmbeddingDimensionError, match="returned 2 dimensions"):
    validate_embedding_dimensions(
      embedding=[0.1, 0.2],
      expected_dimensions=3,
      model="test-embedding",
    )


def test_replace_markdown_document_removes_existing_chunks_for_path(
    session: Session,
    tmp_path: Path,
) -> None:
  path = tmp_path / "cafes.md"
  path.write_text("First paragraph.\n\nSecond paragraph.")
  client = FakeEmbeddingClient()

  first_count = replace_markdown_document(
    session=session,
    path=path,
    metadata={"country": "japan", "city": "kyoto", "doc_type": "cafes"},
    client=client,
    embedding_model="test",
    embedding_dimensions=1024,
  )
  path.write_text("Updated paragraph.")
  second_count = replace_markdown_document(
    session=session,
    path=path,
    metadata={"country": "japan", "city": "kyoto", "doc_type": "cafes"},
    client=client,
    embedding_model="test",
    embedding_dimensions=1024,
  )

  rows = session.scalars(select(RagChunkModel)).all()

  assert first_count == 1
  assert second_count == 1
  assert len(rows) == 1
  assert rows[0].text == "Updated paragraph."
