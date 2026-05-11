from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from northstar.research.ports import ResearchAgent, ResearchFetcher
from northstar.research.schemas import (
  ResearchDraft,
  ResearchTarget,
  ResearchValidationReport,
  TrustRating,
)
from northstar.research.store import (
  SavedResearchRun,
  create_research_run,
  save_candidate_options,
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


def run_research_pipeline(
    *,
    session: Session,
    target: ResearchTarget,
    model_name: str,
    fetcher: ResearchFetcher,
    research_agent: ResearchAgent,
    publish_notes: bool = False,
    note_publisher: NotePublisher | None = None,
) -> ResearchPipelineResult:
  run = create_research_run(session, target=target, model_name=model_name)
  source_texts = fetcher.fetch_texts(target=target)
  draft = research_agent.research(target=target, source_texts=source_texts)
  validation = validate_research_draft(draft)

  if not validation.passed:
    failed_run = update_research_run_status(
      session,
      run_id=run.run_id,
      status="failed",
      report={
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
      publish_notes=publish_notes,
      published_notes=published_notes,
    ),
  )

  return ResearchPipelineResult(
    run=completed_run,
    draft=draft,
    validation=validation,
  )
