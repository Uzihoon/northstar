import pytest

from northstar.rag.store import EmbeddingDimensionError, validate_embedding_dimensions


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
