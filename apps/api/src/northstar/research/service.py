from dataclasses import dataclass

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


@dataclass(frozen=True)
class ResearchPipelineResult:
  run: SavedResearchRun
  draft: ResearchDraft
  validation: ResearchValidationReport


def _build_completion_report(
    *,
    draft: ResearchDraft,
    publish_notes: bool,
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

  return {
    "stable_notes": len(draft.stable_notes),
    "candidates": len(publishable_candidates),
    "blocked_items": len(draft.blocked_items) + len(blocked_candidates),
    "publish_notes": publish_notes,
  }


def run_research_pipeline(
    *,
    session: Session,
    target: ResearchTarget,
    model_name: str,
    fetcher: ResearchFetcher,
    research_agent: ResearchAgent,
    publish_notes: bool = False,
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
  completed_run = update_research_run_status(
    session,
    run_id=run.run_id,
    status="completed",
    report=_build_completion_report(
      draft=draft,
      publish_notes=publish_notes,
    ),
  )

  return ResearchPipelineResult(
    run=completed_run,
    draft=draft,
    validation=validation,
  )
