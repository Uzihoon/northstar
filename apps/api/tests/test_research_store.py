from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.research.schemas import (
  CandidateOption,
  PriceLevel,
  ResearchTarget,
  ResearchTheme,
  TrustRating,
)
from northstar.research.store import (
  create_research_run,
  get_research_run,
  list_research_runs,
  save_candidate_options,
  search_candidate_options,
)


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


def test_create_research_run_persists_target(session: Session) -> None:
  run = create_research_run(
    session,
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
      trusted_urls=["https://kyoto.travel/en/"],
    ),
    model_name="gemma4:e4b",
  )

  loaded = get_research_run(session, run_id=run.run_id)

  assert loaded is not None
  assert loaded.run_id == run.run_id
  assert loaded.target["city"] == "Kyoto"
  assert loaded.status == "created"


def test_search_candidate_options_filters_by_city_category_and_trust(session: Session) -> None:
  run = create_research_run(
    session,
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    model_name="gemma4:e4b",
  )
  save_candidate_options(
    session,
    run_id=run.run_id,
    candidates=[
      CandidateOption(
        name="Quiet Coffee",
        category="cafe",
        country="Japan",
        city="Kyoto",
        area="Higashiyama",
        description="Quiet cafe for scenic breaks.",
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
        description="Should not be stored by service later, but store search must ignore blocked.",
        price_level=PriceLevel.varies,
        trust_rating=TrustRating.blocked,
        source_urls=["https://example.com/blocked"],
      ),
    ],
  )

  results = search_candidate_options(
    session,
    country="Japan",
    city="Kyoto",
    category="cafe",
    min_trust=TrustRating.medium,
  )

  assert [result.name for result in results] == ["Quiet Coffee"]


def test_list_research_runs_returns_newest_first(session: Session) -> None:
  first = create_research_run(
    session,
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    model_name="model-a",
  )
  second = create_research_run(
    session,
    target=ResearchTarget(
      country="South Korea",
      city="Seoul",
      themes=[ResearchTheme.restaurants],
    ),
    model_name="model-b",
  )

  runs = list_research_runs(session)

  assert [run.run_id for run in runs] == [second.run_id, first.run_id]
