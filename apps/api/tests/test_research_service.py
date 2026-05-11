from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.research.models import ResearchCandidateModel
from northstar.research.schemas import (
  BlockedResearchItem,
  CandidateOption,
  PriceLevel,
  ResearchDraft,
  ResearchTarget,
  ResearchTheme,
  SourceReference,
  StableNoteDraft,
  TrustRating,
)
from northstar.research.service import run_research_pipeline
from northstar.research.store import get_research_run


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


class FakeResearchAgent:
  def research(self, *, target: ResearchTarget, source_texts: list[str]) -> ResearchDraft:
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
          description="Critic rejected this.",
          price_level=PriceLevel.varies,
          trust_rating=TrustRating.blocked,
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
  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    return ["Kyoto cafe source text."]


def test_run_research_pipeline_stores_non_blocked_candidates(session: Session) -> None:
  published_notes = []

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
    research_agent=FakeResearchAgent(),
    publish_notes=True,
    note_publisher=fake_note_publisher,
  )

  run = get_research_run(session, run_id=result.run.run_id)
  candidates = session.scalars(select(ResearchCandidateModel)).all()

  assert result.run.status == "completed"
  assert result.validation.passed is True
  assert run is not None
  assert run.status == "completed"
  assert run.report == {
    "stable_notes": 1,
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
  assert published_notes[0]["target"].city == "Kyoto"
  assert published_notes[0]["notes"][0].title == "Kyoto cafe strategy"
