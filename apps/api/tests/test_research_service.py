from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.research.models import ResearchCandidateModel
from northstar.research.fetcher import FetchedSourceDocument, SourceFetchFailure
from northstar.research.schemas import (
  BlockedResearchItem,
  CandidateOption,
  PriceLevel,
  ResearchCritique,
  ResearchReviewIssue,
  ResearchDraft,
  ResearchTarget,
  ResearchTheme,
  SourceReference,
  StableNoteDraft,
  TrustRating,
)
from northstar.research.service import run_research_pipeline
from northstar.research.store import get_research_run, list_source_snapshots


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


class FakeResearchAgent:
  def __init__(self) -> None:
    self.source_texts: list[str] = []

  def research(self, *, target: ResearchTarget, source_texts: list[str]) -> ResearchDraft:
    self.source_texts = source_texts
    return ResearchDraft(
      target=target,
      stable_notes=[
        StableNoteDraft(
          theme=ResearchTheme.cafes,
          title="Kyoto cafe strategy",
          markdown="## Cafe Areas\n\nKawaramachi works well for flexible cafe backups.",
          trust_rating=TrustRating.medium,
          sources=[SourceReference(title="Kyoto guide", url="https://example.com/kyoto")],
        )
      ],
      candidates=[
        CandidateOption(
          name="Quiet Coffee",
          category="cafe",
          country="Japan",
          city="Kyoto",
          area="Kawaramachi",
          description="Central cafe option.",
          price_level=PriceLevel.moderate,
          trust_rating=TrustRating.medium,
          source_urls=["https://example.com/quiet-coffee"],
        ),
        CandidateOption(
          name="Blocked Coffee",
          category="cafe",
          country="Japan",
          city="Kyoto",
          area="Gion",
          description="The draft incorrectly approved this.",
          price_level=PriceLevel.varies,
          trust_rating=TrustRating.medium,
          source_urls=["https://example.com/blocked"],
        ),
      ],
      blocked_items=[
        BlockedResearchItem(
          title="Unsourced cafe list",
          reason="No source URL supported the listed cafes.",
          source_urls=["https://example.com/blocked-list"],
        )
      ],
    )


class FakeFetcher:
  def fetch_documents(self, *, target: ResearchTarget) -> list[FetchedSourceDocument]:
    return [
      FetchedSourceDocument(
        url="https://example.com/kyoto",
        title="Kyoto guide",
        text="Kyoto cafe source text.",
        content_hash="abc123",
        query="Kyoto Japan official travel cafes",
        source_kind="search_result",
        trust_hint="low",
        snippet="Cafe source snippet.",
      )
    ]


class FakeFetcherWithFailure(FakeFetcher):
  fetch_failures = [
    SourceFetchFailure(
      url="https://example.com/unavailable",
      title="Unavailable guide",
      error="Server error (502)",
      source_kind="trusted_url",
      trust_hint="high",
      snippet="Operator supplied trusted URL.",
    )
  ]


class FakeCritic:
  def review(
      self,
      *,
      target: ResearchTarget,
      draft: ResearchDraft,
      source_texts: list[str],
  ) -> ResearchCritique:
    reviewed_candidates = [
      draft.candidates[0],
      draft.candidates[1].model_copy(update={"trust_rating": TrustRating.blocked}),
    ]

    return ResearchCritique(
      summary="Blocked one weak candidate after source review.",
      issues=[
        ResearchReviewIssue(
          path="candidates.1",
          severity="error",
          action="block",
          reason="Source did not support this cafe recommendation.",
          source_urls=["https://example.com/blocked"],
        )
      ],
      reviewed_draft=draft.model_copy(update={"candidates": reviewed_candidates}),
    )


def test_run_research_pipeline_stores_non_blocked_candidates(session: Session) -> None:
  published_notes = []
  research_agent = FakeResearchAgent()

  def fake_note_publisher(*, session, target, notes):
    published_notes.append({
      "target": target,
      "notes": notes,
    })
    return [
      {
        "path": "rag_docs/japan/kyoto/cafes.md",
        "chunks": 2,
      }
    ]

  result = run_research_pipeline(
    session=session,
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    model_name="test-model",
    fetcher=FakeFetcher(),
    research_agent=research_agent,
    critic=FakeCritic(),
    publish_notes=True,
    note_publisher=fake_note_publisher,
  )

  run = get_research_run(session, run_id=result.run.run_id)
  candidates = session.scalars(select(ResearchCandidateModel)).all()
  source_snapshots = list_source_snapshots(session, run_id=result.run.run_id)

  assert result.run.status == "completed"
  assert result.validation.passed is True
  assert run is not None
  assert run.status == "completed"
  assert run.report == {
    "stable_notes": 1,
    "source_snapshots": 1,
    "critic": {
      "summary": "Blocked one weak candidate after source review.",
      "issues": [
        {
          "path": "candidates.1",
          "severity": "error",
          "action": "block",
          "reason": "Source did not support this cafe recommendation.",
          "source_urls": ["https://example.com/blocked"],
        }
      ],
    },
    "candidates": 1,
    "blocked_items": 2,
    "publish_notes": True,
    "published_note_paths": ["rag_docs/japan/kyoto/cafes.md"],
    "published_note_chunks": 2,
    "stable_note_titles": ["Kyoto cafe strategy"],
    "candidate_names": ["Quiet Coffee"],
    "blocked_item_details": [
      {
        "title": "Unsourced cafe list",
        "reason": "No source URL supported the listed cafes.",
        "source_urls": ["https://example.com/blocked-list"],
      },
      {
        "title": "Blocked Coffee",
        "reason": "Candidate marked blocked by critic.",
        "source_urls": ["https://example.com/blocked"],
      },
    ],
  }
  assert [candidate.name for candidate in candidates] == ["Quiet Coffee"]
  assert len(source_snapshots) == 1
  assert source_snapshots[0].url == "https://example.com/kyoto"
  assert source_snapshots[0].metadata["query"] == "Kyoto Japan official travel cafes"
  assert "Source URL: https://example.com/kyoto" in research_agent.source_texts[0]
  assert "Kyoto cafe source text." in research_agent.source_texts[0]
  assert published_notes[0]["target"].city == "Kyoto"
  assert published_notes[0]["notes"][0].title == "Kyoto cafe strategy"


def test_run_existing_research_pipeline_uses_existing_run_id(session: Session) -> None:
  from northstar.research.service import run_existing_research_pipeline
  from northstar.research.store import create_research_run

  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
  )
  run = create_research_run(
    session,
    target=target,
    model_name="test-model",
    status="queued",
  )

  result = run_existing_research_pipeline(
    session=session,
    run_id=run.run_id,
    target=target,
    model_name="test-model",
    fetcher=FakeFetcher(),
    research_agent=FakeResearchAgent(),
    critic=FakeCritic(),
  )

  assert result.run.run_id == run.run_id
  assert result.run.status == "completed"


def test_run_research_pipeline_reports_source_fetch_failures(session: Session) -> None:
  result = run_research_pipeline(
    session=session,
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    model_name="test-model",
    fetcher=FakeFetcherWithFailure(),
    research_agent=FakeResearchAgent(),
    critic=FakeCritic(),
  )

  assert result.run.status == "completed"
  assert result.run.report["source_fetch_failures"] == [
    {
      "url": "https://example.com/unavailable",
      "title": "Unavailable guide",
      "error": "Server error (502)",
      "query": None,
      "source_kind": "trusted_url",
      "trust_hint": "high",
      "snippet": "Operator supplied trusted URL.",
    }
  ]
