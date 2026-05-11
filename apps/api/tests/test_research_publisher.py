from pathlib import Path

from northstar.research.publisher import publish_stable_notes, stable_note_path
from northstar.research.schemas import (
  ResearchTarget,
  ResearchTheme,
  SourceReference,
  StableNoteDraft,
  TrustRating,
)


def test_stable_note_path_uses_rag_docs_country_city_theme() -> None:
  path = stable_note_path(
    base_dir=Path("rag_docs"),
    target=ResearchTarget(
      country="South Korea",
      city="Seoul",
      themes=[ResearchTheme.cafes],
    ),
    theme=ResearchTheme.cafes,
  )

  assert path == Path("rag_docs/south-korea/seoul/cafes.md")


def test_publish_stable_notes_writes_markdown_and_replaces_rag_chunks(tmp_path: Path) -> None:
  calls = []

  def fake_replace_markdown_document(**kwargs):
    calls.append(kwargs)
    return 2

  note = StableNoteDraft(
    theme=ResearchTheme.cafes,
    title="Kyoto cafe strategy",
    markdown="## Cafe Areas\n\nKawaramachi works well for flexible cafe backups.",
    trust_rating=TrustRating.medium,
    sources=[
      SourceReference(
        title="Kyoto Travel",
        url="https://kyoto.travel/en/",
      )
    ],
  )
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
  )

  published = publish_stable_notes(
    session=object(),
    target=target,
    notes=[note],
    base_dir=tmp_path,
    client=object(),
    embedding_model="test-embedding",
    embedding_dimensions=1024,
    replace_fn=fake_replace_markdown_document,
  )

  note_path = tmp_path / "japan" / "kyoto" / "cafes.md"

  assert published[0].path == str(note_path)
  assert published[0].chunks == 2
  assert note_path.read_text() == """---
country: Japan
city: Kyoto
theme: cafes
trust_rating: medium
sources:
  - title: Kyoto Travel
    url: https://kyoto.travel/en/
---

# Kyoto cafe strategy

## Cafe Areas

Kawaramachi works well for flexible cafe backups.
"""
  assert calls[0]["path"] == note_path
  assert calls[0]["metadata"] == {
    "country": "japan",
    "city": "kyoto",
    "doc_type": "cafes",
    "source_type": "curated_markdown",
  }
