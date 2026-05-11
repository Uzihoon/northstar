from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from northstar.ollama_client import OllamaClient
from northstar.rag.metadata import build_rag_metadata, normalize_slug
from northstar.rag.store import replace_markdown_document
from northstar.research.schemas import ResearchTarget, ResearchTheme, StableNoteDraft


ReplaceMarkdownDocumentFn = Callable[..., int]


@dataclass(frozen=True)
class PublishedStableNote:
  path: str
  chunks: int


def stable_note_path(
    *,
    base_dir: Path,
    target: ResearchTarget,
    theme: ResearchTheme,
) -> Path:
  country = normalize_slug(target.country) or "unknown-country"
  city = normalize_slug(target.city) or "unknown-city"
  return base_dir / country / city / f"{theme.value}.md"


def _format_sources(note: StableNoteDraft) -> str:
  if not note.sources:
    return "sources: []"

  lines = ["sources:"]
  for source in note.sources:
    lines.append(f"  - title: {source.title}")
    lines.append(f"    url: {source.url}")

  return "\n".join(lines)


def format_stable_note_markdown(*, target: ResearchTarget, note: StableNoteDraft) -> str:
  markdown = note.markdown.strip()

  return f"""---
country: {target.country}
city: {target.city}
theme: {note.theme.value}
trust_rating: {note.trust_rating.value}
{_format_sources(note)}
---

# {note.title}

{markdown}
"""


def publish_stable_notes(
    *,
    session: Session,
    target: ResearchTarget,
    notes: list[StableNoteDraft],
    base_dir: Path,
    client: OllamaClient,
    embedding_model: str,
    embedding_dimensions: int,
    replace_fn: ReplaceMarkdownDocumentFn = replace_markdown_document,
) -> list[PublishedStableNote]:
  published: list[PublishedStableNote] = []

  for note in notes:
    path = stable_note_path(
      base_dir=base_dir,
      target=target,
      theme=note.theme,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_stable_note_markdown(target=target, note=note))

    chunks = replace_fn(
      session=session,
      path=path,
      metadata=build_rag_metadata(
        path=path,
        country=target.country,
        city=target.city,
        doc_type=note.theme.value,
      ),
      client=client,
      embedding_model=embedding_model,
      embedding_dimensions=embedding_dimensions,
    )
    published.append(PublishedStableNote(path=str(path), chunks=chunks))

  return published
