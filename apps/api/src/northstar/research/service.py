from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from northstar.research.fetcher import FetchedSourceDocument, hash_text
from northstar.research.ports import ResearchAgent, ResearchCritic, ResearchFetcher
from northstar.research.schemas import (
  ResearchCritique,
  ResearchDraft,
  ResearchTarget,
  ResearchValidationReport,
  TrustRating,
)
from northstar.research.store import (
  FetchedSourceSnapshot,
  SavedResearchRun,
  create_research_run,
  save_candidate_options,
  save_source_snapshots,
  update_research_run_status,
)
from northstar.research.validator import validate_research_draft

NotePublisher = Callable[..., list[Any]]


@dataclass(frozen=True)
class ResearchPipelineResult:
  run: SavedResearchRun
  draft: ResearchDraft
  validation: ResearchValidationReport


def _build_completion_report(
    *,
    draft: ResearchDraft,
    source_snapshot_count: int,
    critique: ResearchCritique | None,
    publish_notes: bool,
    published_notes: list[Any],
) -> dict[str, object]:
  publishable_candidates = [
    candidate
    for candidate in draft.candidates
    if candidate.trust_rating != TrustRating.blocked
  ]
  blocked_candidates = [
    candidate
    for candidate in draft.candidates
    if candidate.trust_rating == TrustRating.blocked
  ]
  blocked_item_details = [
    item.model_dump(mode="json")
    for item in draft.blocked_items
  ] + [
    {
      "title": candidate.name,
      "reason": "Candidate marked blocked by critic.",
      "source_urls": candidate.source_urls,
    }
    for candidate in blocked_candidates
  ]

  return {
    "stable_notes": len(draft.stable_notes),
    "source_snapshots": source_snapshot_count,
    "critic": _critic_report(critique),
    "candidates": len(publishable_candidates),
    "blocked_items": len(draft.blocked_items) + len(blocked_candidates),
    "publish_notes": publish_notes,
    "published_note_paths": [
      note["path"] if isinstance(note, dict) else note.path
      for note in published_notes
    ],
    "published_note_chunks": sum(
      int(note["chunks"] if isinstance(note, dict) else note.chunks)
      for note in published_notes
    ),
    "stable_note_titles": [
      note.title
      for note in draft.stable_notes
    ],
    "candidate_names": [
      candidate.name
      for candidate in publishable_candidates
    ],
    "blocked_item_details": blocked_item_details,
  }


def _critic_report(critique: ResearchCritique | None) -> dict[str, object] | None:
  if critique is None:
    return None

  return {
    "summary": critique.summary,
    "issues": [
      issue.model_dump(mode="json")
      for issue in critique.issues
    ],
  }


def _fetch_source_documents(
    *,
    fetcher: ResearchFetcher,
    target: ResearchTarget,
) -> list[FetchedSourceDocument]:
  if hasattr(fetcher, "fetch_documents"):
    return fetcher.fetch_documents(target=target)

  return [
    FetchedSourceDocument(
      url=f"source-{index + 1}",
      title=f"Source {index + 1}",
      text=text,
      content_hash=hash_text(text),
      source_kind="legacy_text",
    )
    for index, text in enumerate(fetcher.fetch_texts(target=target))
  ]


def _snapshot_from_document(document: FetchedSourceDocument) -> FetchedSourceSnapshot:
  return FetchedSourceSnapshot(
    url=document.url,
    title=document.title,
    content_hash=document.content_hash,
    extracted_text=document.text,
    fetched_at=document.fetched_at,
    metadata={
      "query": document.query,
      "source_kind": document.source_kind,
      "trust_hint": document.trust_hint,
      "snippet": document.snippet,
    },
  )


def _format_source_document_for_agent(document: FetchedSourceDocument) -> str:
  metadata_lines = [
    f"Source URL: {document.url}",
    f"Source title: {document.title or 'Untitled'}",
    f"Source kind: {document.source_kind}",
  ]

  if document.query:
    metadata_lines.append(f"Discovery query: {document.query}")

  if document.trust_hint:
    metadata_lines.append(f"Trust hint: {document.trust_hint}")

  return "\n".join([
    *metadata_lines,
    "",
    document.text,
  ])


def run_research_pipeline(
    *,
    session: Session,
    target: ResearchTarget,
    model_name: str,
    fetcher: ResearchFetcher,
    research_agent: ResearchAgent,
    critic: ResearchCritic | None = None,
    publish_notes: bool = False,
    note_publisher: NotePublisher | None = None,
) -> ResearchPipelineResult:
  run = create_research_run(session, target=target, model_name=model_name)
  source_documents = _fetch_source_documents(fetcher=fetcher, target=target)
  source_snapshots = save_source_snapshots(
    session,
    run_id=run.run_id,
    sources=[
      _snapshot_from_document(document)
      for document in source_documents
    ],
  )
  source_texts = [
    _format_source_document_for_agent(document)
    for document in source_documents
  ]
  draft = research_agent.research(target=target, source_texts=source_texts)
  critique = None

  if critic is not None:
    critique = critic.review(
      target=target,
      draft=draft,
      source_texts=source_texts,
    )
    draft = critique.reviewed_draft

  validation = validate_research_draft(draft)

  if not validation.passed:
    failed_run = update_research_run_status(
      session,
      run_id=run.run_id,
      status="failed",
      report={
        "source_snapshots": len(source_snapshots),
        "critic": _critic_report(critique),
        "validation": validation.model_dump(mode="json"),
      },
    )
    return ResearchPipelineResult(
      run=failed_run,
      draft=draft,
      validation=validation,
    )

  save_candidate_options(
    session,
    run_id=run.run_id,
    candidates=[
      candidate
      for candidate in draft.candidates
      if candidate.trust_rating != TrustRating.blocked
    ],
  )
  published_notes = []
  if publish_notes and note_publisher is not None:
    published_notes = note_publisher(
      session=session,
      target=target,
      notes=draft.stable_notes,
    )

  completed_run = update_research_run_status(
    session,
    run_id=run.run_id,
    status="completed",
    report=_build_completion_report(
      draft=draft,
      source_snapshot_count=len(source_snapshots),
      critique=critique,
      publish_notes=publish_notes,
      published_notes=published_notes,
    ),
  )

  return ResearchPipelineResult(
    run=completed_run,
    draft=draft,
    validation=validation,
  )
