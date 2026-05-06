from pathlib import Path

from northstar.rag.metadata import build_rag_metadata, infer_rag_metadata_from_path


def test_infer_rag_metadata_from_path() -> None:
  metadata = infer_rag_metadata_from_path(
    Path("rag_docs/japan/kyoto/cafes.md")
  )

  assert metadata == {
    "country": "japan",
    "city": "kyoto",
    "doc_type": "cafes",
    "source_type": "curated_markdown",
  }


def test_build_rag_metadata_allows_explicit_overrides() -> None:
  metadata = build_rag_metadata(
    path=Path("rag_docs/japan/kyoto/cafes.md"),
    country="South Korea",
    city="Seoul",
    doc_type="Restaurants",
  )

  assert metadata["country"] == "south-korea"
  assert metadata["city"] == "seoul"
  assert metadata["doc_type"] == "restaurants"
