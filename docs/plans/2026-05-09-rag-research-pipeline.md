# RAG Research Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a backend research pipeline that generates stable RAG notes, stores specific travel candidates, and lets the planner access candidates through a safe tool.

**Architecture:** Add a `northstar.research` package for schemas, validation, source gathering ports, LLM drafting/review, publishing, and persistence. Stable knowledge is written to Markdown and ingested into pgvector RAG; specific cafes, restaurants, accommodations, and other options are stored as structured candidates with trust labels and source URLs.

**Tech Stack:** Python 3.12, Typer, FastAPI later, SQLAlchemy, Alembic, Pydantic, Ollama structured output, existing RAG store, existing agent tool registry.

---

### Task 1: Research Schemas And Validator

**Files:**
- Create: `apps/api/src/northstar/research/__init__.py`
- Create: `apps/api/src/northstar/research/schemas.py`
- Create: `apps/api/src/northstar/research/validator.py`
- Test: `apps/api/tests/test_research_validator.py`

**Step 1: Write failing tests**

Create `apps/api/tests/test_research_validator.py`:

```python
from northstar.research.schemas import (
  CandidateOption,
  PriceLevel,
  ResearchDraft,
  ResearchTarget,
  ResearchTheme,
  SourceReference,
  StableNoteDraft,
  TrustRating,
)
from northstar.research.validator import validate_research_draft


def test_validate_research_draft_accepts_sourced_notes_and_candidates() -> None:
  source = SourceReference(
    title="Kyoto Travel",
    url="https://kyoto.travel/en/",
  )
  draft = ResearchDraft(
    target=ResearchTarget(country="Japan", city="Kyoto", themes=[ResearchTheme.cafes]),
    stable_notes=[
      StableNoteDraft(
        theme=ResearchTheme.cafes,
        title="Kyoto cafe strategy",
        markdown="## Cafe Areas\n\nHigashiyama works well for scenic breaks.",
        trust_rating=TrustRating.high,
        sources=[source],
      )
    ],
    candidates=[
      CandidateOption(
        name="Example Coffee",
        category="cafe",
        country="Japan",
        city="Kyoto",
        area="Kawaramachi",
        description="Central coffee stop.",
        price_level=PriceLevel.moderate,
        trust_rating=TrustRating.medium,
        source_urls=["https://example.com/cafe"],
      )
    ],
  )

  report = validate_research_draft(draft)

  assert report.passed is True
  assert report.issues == []


def test_validate_research_draft_blocks_missing_sources() -> None:
  draft = ResearchDraft(
    target=ResearchTarget(country="Japan", city="Kyoto", themes=[ResearchTheme.cafes]),
    stable_notes=[
      StableNoteDraft(
        theme=ResearchTheme.cafes,
        title="Unsourced note",
        markdown="## Cafe Areas\n\nTrust me.",
        trust_rating=TrustRating.medium,
        sources=[],
      )
    ],
  )

  report = validate_research_draft(draft)

  assert report.passed is False
  assert report.issues[0].code == "missing_sources"


def test_validate_research_draft_rejects_exact_prices_in_stable_notes() -> None:
  draft = ResearchDraft(
    target=ResearchTarget(country="Japan", city="Kyoto", themes=[ResearchTheme.overview]),
    stable_notes=[
      StableNoteDraft(
        theme=ResearchTheme.overview,
        title="Budget note",
        markdown="Temple entry is 600 yen.",
        trust_rating=TrustRating.high,
        sources=[SourceReference(title="Source", url="https://example.com")],
      )
    ],
  )

  report = validate_research_draft(draft)

  assert report.passed is False
  assert report.issues[0].code == "exact_price_in_stable_note"
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_validator.py -q
```

Expected: FAIL because `northstar.research` does not exist.

**Step 3: Implement schemas**

Create `apps/api/src/northstar/research/__init__.py`:

```python
"""Research pipeline for backfilling and refreshing travel knowledge."""
```

Create `apps/api/src/northstar/research/schemas.py`:

```python
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
  return datetime.now(timezone.utc)


class ResearchTheme(str, Enum):
  overview = "overview"
  neighborhoods = "neighborhoods"
  cafes = "cafes"
  restaurants = "restaurants"
  sightseeing = "sightseeing"
  transport = "transport"
  accommodation = "accommodation"


class TrustRating(str, Enum):
  high = "high"
  medium = "medium"
  low = "low"
  blocked = "blocked"


class PriceLevel(str, Enum):
  free = "free"
  budget = "budget"
  moderate = "moderate"
  expensive = "expensive"
  luxury = "luxury"
  varies = "varies"


class CandidateCategory(str, Enum):
  cafe = "cafe"
  restaurant = "restaurant"
  accommodation = "accommodation"
  attraction = "attraction"
  shop = "shop"
  other = "other"


class SourceReference(BaseModel):
  title: str
  url: str
  fetched_at: datetime | None = None
  content_hash: str | None = None
  trust_hint: TrustRating | None = None


class ResearchTarget(BaseModel):
  country: str
  city: str
  themes: list[ResearchTheme] = Field(default_factory=lambda: list(ResearchTheme))
  trusted_urls: list[str] = Field(default_factory=list)


class StableNoteDraft(BaseModel):
  theme: ResearchTheme
  title: str
  markdown: str
  trust_rating: TrustRating
  sources: list[SourceReference] = Field(default_factory=list)


class CandidateOption(BaseModel):
  name: str
  category: CandidateCategory | str
  country: str
  city: str
  area: str | None = None
  description: str
  price_level: PriceLevel = PriceLevel.varies
  trust_rating: TrustRating
  source_urls: list[str] = Field(default_factory=list)
  last_checked_at: datetime = Field(default_factory=utc_now)
  metadata: dict[str, object] = Field(default_factory=dict)


class BlockedResearchItem(BaseModel):
  title: str
  reason: str
  source_urls: list[str] = Field(default_factory=list)


class ResearchDraft(BaseModel):
  target: ResearchTarget
  stable_notes: list[StableNoteDraft] = Field(default_factory=list)
  candidates: list[CandidateOption] = Field(default_factory=list)
  blocked_items: list[BlockedResearchItem] = Field(default_factory=list)


class ResearchValidationIssue(BaseModel):
  code: str
  path: str
  message: str


class ResearchValidationReport(BaseModel):
  passed: bool
  issues: list[ResearchValidationIssue] = Field(default_factory=list)
```

Create `apps/api/src/northstar/research/validator.py`:

```python
import re

from northstar.research.schemas import (
  ResearchDraft,
  ResearchValidationIssue,
  ResearchValidationReport,
  TrustRating,
)

EXACT_PRICE_PATTERN = re.compile(
  r"(\$|€|£|¥|\bUSD\b|\bEUR\b|\bJPY\b|\byen\b|\bdollars?\b)\s?\d+|\d+\s?(yen|dollars?|usd|eur|jpy)",
  re.IGNORECASE,
)


def _issue(*, code: str, path: str, message: str) -> ResearchValidationIssue:
  return ResearchValidationIssue(code=code, path=path, message=message)


def validate_research_draft(draft: ResearchDraft) -> ResearchValidationReport:
  issues: list[ResearchValidationIssue] = []

  for index, note in enumerate(draft.stable_notes):
    path = f"stable_notes.{index}"

    if note.trust_rating == TrustRating.blocked:
      issues.append(
        _issue(
          code="blocked_note_in_publishable_draft",
          path=path,
          message="Blocked stable notes must stay in blocked_items.",
        )
      )

    if not note.sources:
      issues.append(
        _issue(
          code="missing_sources",
          path=f"{path}.sources",
          message="Stable notes must include source references.",
        )
      )

    if EXACT_PRICE_PATTERN.search(note.markdown):
      issues.append(
        _issue(
          code="exact_price_in_stable_note",
          path=f"{path}.markdown",
          message="Stable notes should use price levels instead of exact prices.",
        )
      )

  for index, candidate in enumerate(draft.candidates):
    path = f"candidates.{index}"

    if candidate.trust_rating == TrustRating.blocked:
      issues.append(
        _issue(
          code="blocked_candidate_in_publishable_draft",
          path=path,
          message="Blocked candidates must stay in blocked_items.",
        )
      )

    if not candidate.source_urls:
      issues.append(
        _issue(
          code="missing_candidate_sources",
          path=f"{path}.source_urls",
          message="Candidates must include at least one source URL.",
        )
      )

  return ResearchValidationReport(passed=not issues, issues=issues)
```

**Step 4: Run test to verify it passes**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_validator.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/northstar/research apps/api/tests/test_research_validator.py
git commit -m "feat: add research draft validation"
```

---

### Task 2: Research Persistence Models And Store

**Files:**
- Create: `apps/api/src/northstar/research/models.py`
- Create: `apps/api/src/northstar/research/store.py`
- Modify: `apps/api/migrations/env.py`
- Create: `apps/api/migrations/versions/d7b8c3f2a901_add_research_pipeline_tables.py`
- Test: `apps/api/tests/test_research_store.py`

**Step 1: Write failing store tests**

Create `apps/api/tests/test_research_store.py`:

```python
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
  SourceReference,
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
    target=ResearchTarget(country="Japan", city="Kyoto", themes=[ResearchTheme.cafes]),
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
    target=ResearchTarget(country="Japan", city="Kyoto", themes=[ResearchTheme.cafes]),
    model_name="model-a",
  )
  second = create_research_run(
    session,
    target=ResearchTarget(country="South Korea", city="Seoul", themes=[ResearchTheme.restaurants]),
    model_name="model-b",
  )

  runs = list_research_runs(session)

  assert [run.run_id for run in runs] == [second.run_id, first.run_id]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_store.py -q
```

Expected: FAIL because persistence does not exist.

**Step 3: Implement models**

Create `apps/api/src/northstar/research/models.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from northstar.db import Base


def utc_now() -> datetime:
  return datetime.now(timezone.utc)


class ResearchRunModel(Base):
  __tablename__ = "research_runs"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  target: Mapped[dict[str, object]] = mapped_column(JSON)
  model_name: Mapped[str] = mapped_column(String(128))
  status: Mapped[str] = mapped_column(String(32), index=True, default="created")
  report: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

  source_snapshots: Mapped[list["ResearchSourceSnapshotModel"]] = relationship(
    back_populates="run",
    cascade="all, delete-orphan",
  )
  candidates: Mapped[list["ResearchCandidateModel"]] = relationship(
    back_populates="run",
    cascade="all, delete-orphan",
  )


class ResearchSourceSnapshotModel(Base):
  __tablename__ = "research_source_snapshots"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), index=True)
  url: Mapped[str] = mapped_column(Text)
  title: Mapped[str | None] = mapped_column(Text, nullable=True)
  content_hash: Mapped[str] = mapped_column(String(64), index=True)
  extracted_text: Mapped[str] = mapped_column(Text)
  fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  run: Mapped[ResearchRunModel] = relationship(back_populates="source_snapshots")


class ResearchCandidateModel(Base):
  __tablename__ = "research_candidates"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), index=True)
  country: Mapped[str] = mapped_column(String(128), index=True)
  city: Mapped[str] = mapped_column(String(128), index=True)
  category: Mapped[str] = mapped_column(String(64), index=True)
  name: Mapped[str] = mapped_column(Text)
  area: Mapped[str | None] = mapped_column(Text, nullable=True)
  description: Mapped[str] = mapped_column(Text)
  price_level: Mapped[str] = mapped_column(String(32), index=True)
  trust_rating: Mapped[str] = mapped_column(String(32), index=True)
  source_urls: Mapped[list[str]] = mapped_column(JSON)
  last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  candidate_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  run: Mapped[ResearchRunModel] = relationship(back_populates="candidates")
```

Modify `apps/api/migrations/env.py`:

```python
import northstar.research.models  # noqa: F401
```

**Step 4: Implement store**

Create `apps/api/src/northstar/research/store.py`:

```python
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from northstar.research.models import ResearchCandidateModel, ResearchRunModel
from northstar.research.schemas import CandidateOption, ResearchTarget, TrustRating


TRUST_ORDER = {
  TrustRating.low: 1,
  TrustRating.medium: 2,
  TrustRating.high: 3,
}


@dataclass(frozen=True)
class SavedResearchRun:
  run_id: str
  target: dict[str, object]
  model_name: str
  status: str
  report: dict[str, object] | None
  created_at: str
  updated_at: str


@dataclass(frozen=True)
class SavedCandidateOption:
  candidate_id: str
  run_id: str
  name: str
  category: str
  country: str
  city: str
  area: str | None
  description: str
  price_level: str
  trust_rating: str
  source_urls: list[str]
  last_checked_at: str
  metadata: dict[str, object]


def _run_from_model(model: ResearchRunModel) -> SavedResearchRun:
  return SavedResearchRun(
    run_id=model.id,
    target=model.target,
    model_name=model.model_name,
    status=model.status,
    report=model.report,
    created_at=model.created_at.isoformat(),
    updated_at=model.updated_at.isoformat(),
  )


def _candidate_from_model(model: ResearchCandidateModel) -> SavedCandidateOption:
  return SavedCandidateOption(
    candidate_id=model.id,
    run_id=model.run_id,
    name=model.name,
    category=model.category,
    country=model.country,
    city=model.city,
    area=model.area,
    description=model.description,
    price_level=model.price_level,
    trust_rating=model.trust_rating,
    source_urls=model.source_urls,
    last_checked_at=model.last_checked_at.isoformat(),
    metadata=model.candidate_metadata,
  )


def create_research_run(
    session: Session,
    *,
    target: ResearchTarget,
    model_name: str,
) -> SavedResearchRun:
  row = ResearchRunModel(
    target=target.model_dump(mode="json"),
    model_name=model_name,
    status="created",
  )
  session.add(row)
  session.commit()
  session.refresh(row)
  return _run_from_model(row)


def get_research_run(session: Session, *, run_id: str) -> SavedResearchRun | None:
  row = session.get(ResearchRunModel, run_id)
  return _run_from_model(row) if row is not None else None


def list_research_runs(session: Session, *, limit: int = 20) -> list[SavedResearchRun]:
  rows = session.scalars(
    select(ResearchRunModel)
    .order_by(ResearchRunModel.created_at.desc())
    .limit(limit)
  ).all()
  return [_run_from_model(row) for row in rows]


def save_candidate_options(
    session: Session,
    *,
    run_id: str,
    candidates: list[CandidateOption],
) -> list[SavedCandidateOption]:
  rows = [
    ResearchCandidateModel(
      run_id=run_id,
      country=candidate.country,
      city=candidate.city,
      category=str(candidate.category),
      name=candidate.name,
      area=candidate.area,
      description=candidate.description,
      price_level=candidate.price_level.value,
      trust_rating=candidate.trust_rating.value,
      source_urls=candidate.source_urls,
      last_checked_at=candidate.last_checked_at,
      candidate_metadata=candidate.metadata,
    )
    for candidate in candidates
    if candidate.trust_rating != TrustRating.blocked
  ]
  session.add_all(rows)
  session.commit()

  for row in rows:
    session.refresh(row)

  return [_candidate_from_model(row) for row in rows]


def search_candidate_options(
    session: Session,
    *,
    country: str,
    city: str,
    category: str | None = None,
    min_trust: TrustRating = TrustRating.low,
    limit: int = 10,
) -> list[SavedCandidateOption]:
  allowed_ratings = [
    rating.value
    for rating, rank in TRUST_ORDER.items()
    if rank >= TRUST_ORDER[min_trust]
  ]
  statement = select(ResearchCandidateModel).where(
    ResearchCandidateModel.country == country,
    ResearchCandidateModel.city == city,
    ResearchCandidateModel.trust_rating.in_(allowed_ratings),
  )

  if category is not None:
    statement = statement.where(ResearchCandidateModel.category == category)

  rows = session.scalars(
    statement
    .order_by(ResearchCandidateModel.created_at.desc())
    .limit(limit)
  ).all()
  return [_candidate_from_model(row) for row in rows]
```

**Step 5: Add Alembic migration**

Create `apps/api/migrations/versions/d7b8c3f2a901_add_research_pipeline_tables.py` with `down_revision = "a74c2f91d3a8"`. Include tables `research_runs`, `research_source_snapshots`, and `research_candidates` matching the models.

**Step 6: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_store.py -q
uv run pytest -q
```

Expected: PASS.

**Step 7: Commit**

```bash
git add apps/api/src/northstar/research apps/api/migrations/env.py apps/api/migrations/versions/d7b8c3f2a901_add_research_pipeline_tables.py apps/api/tests/test_research_store.py
git commit -m "feat: store research runs and candidates"
```

---

### Task 3: Refresh-Safe RAG Publishing

**Files:**
- Modify: `apps/api/src/northstar/rag/store.py`
- Test: `apps/api/tests/test_rag_store.py`

**Step 1: Write failing tests**

Append to `apps/api/tests/test_rag_store.py`:

```python
from pathlib import Path
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.rag.models import RagChunkModel
from northstar.rag.store import replace_markdown_document


class FakeEmbeddingClient:
  def embed(self, *, text: str, model: str) -> list[float]:
    return [0.1, 0.2, 0.3]


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


def test_replace_markdown_document_removes_existing_chunks_for_path(
    session: Session,
    tmp_path: Path,
) -> None:
  path = tmp_path / "cafes.md"
  path.write_text("First paragraph.\n\nSecond paragraph.")
  client = FakeEmbeddingClient()

  first_count = replace_markdown_document(
    session=session,
    path=path,
    metadata={"country": "japan", "city": "kyoto", "doc_type": "cafes"},
    client=client,
    embedding_model="test",
    embedding_dimensions=3,
  )
  path.write_text("Updated paragraph.")
  second_count = replace_markdown_document(
    session=session,
    path=path,
    metadata={"country": "japan", "city": "kyoto", "doc_type": "cafes"},
    client=client,
    embedding_model="test",
    embedding_dimensions=3,
  )

  rows = session.scalars(select(RagChunkModel)).all()

  assert first_count == 1
  assert second_count == 1
  assert len(rows) == 1
  assert rows[0].text == "Updated paragraph."
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd apps/api
uv run pytest tests/test_rag_store.py::test_replace_markdown_document_removes_existing_chunks_for_path -q
```

Expected: FAIL because `replace_markdown_document` does not exist.

**Step 3: Implement refresh-safe replace**

Modify `apps/api/src/northstar/rag/store.py`:

```python
from sqlalchemy import delete, select
```

Add:

```python
def delete_rag_chunks_for_source_path(*, session: Session, path: Path) -> int:
  result = session.execute(
    delete(RagChunkModel).where(RagChunkModel.source_path == str(path))
  )
  return int(result.rowcount or 0)


def replace_markdown_document(
    *,
    session: Session,
    path: Path,
    metadata: dict[str, object],
    client: OllamaClient,
    embedding_model: str,
    embedding_dimensions: int,
) -> int:
  delete_rag_chunks_for_source_path(session=session, path=path)
  return ingest_markdown_document(
    session=session,
    path=path,
    metadata=metadata,
    client=client,
    embedding_model=embedding_model,
    embedding_dimensions=embedding_dimensions,
  )
```

If SQLite tests fail because `Vector(1024)` does not compile in the in-memory test, adapt the test to avoid `Base.metadata.create_all()` for pgvector or keep this test at the store boundary with a fake session. Do not weaken production code to satisfy SQLite.

**Step 4: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_rag_store.py -q
uv run pytest -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/northstar/rag/store.py apps/api/tests/test_rag_store.py
git commit -m "feat: replace rag chunks on refresh"
```

---

### Task 4: Research Service With Fakeable Search And LLM Ports

**Files:**
- Create: `apps/api/src/northstar/research/ports.py`
- Create: `apps/api/src/northstar/research/service.py`
- Test: `apps/api/tests/test_research_service.py`

**Step 1: Write failing service test**

Create `apps/api/tests/test_research_service.py`:

```python
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.research.models import ResearchCandidateModel
from northstar.research.schemas import (
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
    )


class FakeFetcher:
  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    return ["Kyoto cafe source text."]


def test_run_research_pipeline_stores_non_blocked_candidates(session: Session) -> None:
  result = run_research_pipeline(
    session=session,
    target=ResearchTarget(country="Japan", city="Kyoto", themes=[ResearchTheme.cafes]),
    model_name="test-model",
    fetcher=FakeFetcher(),
    research_agent=FakeResearchAgent(),
    publish_notes=False,
  )

  candidates = session.scalars(select(ResearchCandidateModel)).all()

  assert result.run.status == "completed"
  assert result.validation.passed is True
  assert [candidate.name for candidate in candidates] == ["Quiet Coffee"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_service.py -q
```

Expected: FAIL because service does not exist.

**Step 3: Add ports**

Create `apps/api/src/northstar/research/ports.py`:

```python
from typing import Protocol

from northstar.research.schemas import ResearchDraft, ResearchTarget


class ResearchFetcher(Protocol):
  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    ...


class ResearchAgent(Protocol):
  def research(self, *, target: ResearchTarget, source_texts: list[str]) -> ResearchDraft:
    ...
```

**Step 4: Add service**

Create `apps/api/src/northstar/research/service.py`:

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from northstar.research.ports import ResearchAgent, ResearchFetcher
from northstar.research.schemas import ResearchDraft, ResearchTarget, ResearchValidationReport, TrustRating
from northstar.research.store import SavedResearchRun, create_research_run, save_candidate_options
from northstar.research.validator import validate_research_draft


@dataclass(frozen=True)
class ResearchPipelineResult:
  run: SavedResearchRun
  draft: ResearchDraft
  validation: ResearchValidationReport


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
    # Later task will persist report/status updates. For now keep the failure explicit.
    raise ValueError(validation.model_dump(mode="json"))

  save_candidate_options(
    session,
    run_id=run.run_id,
    candidates=[
      candidate
      for candidate in draft.candidates
      if candidate.trust_rating != TrustRating.blocked
    ],
  )

  completed_run = SavedResearchRun(
    run_id=run.run_id,
    target=run.target,
    model_name=run.model_name,
    status="completed",
    report={
      "stable_notes": len(draft.stable_notes),
      "candidates": len([candidate for candidate in draft.candidates if candidate.trust_rating != TrustRating.blocked]),
      "blocked_items": len(draft.blocked_items),
      "publish_notes": publish_notes,
    },
    created_at=run.created_at,
    updated_at=run.updated_at,
  )

  return ResearchPipelineResult(
    run=completed_run,
    draft=draft,
    validation=validation,
  )
```

Then improve the service to actually update `ResearchRunModel.status/report` instead of returning a synthetic run. Add a focused test for persisted status before committing.

**Step 5: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_service.py -q
uv run pytest -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add apps/api/src/northstar/research apps/api/tests/test_research_service.py
git commit -m "feat: orchestrate research pipeline"
```

---

### Task 5: CLI Commands For Research Runs

**Files:**
- Modify: `apps/api/src/northstar/cli.py`
- Test: `apps/api/tests/test_research_cli.py`

**Step 1: Write CLI tests**

Use `typer.testing.CliRunner` and fake the service/store. Test:

- `northstar research-city Kyoto --country Japan --theme cafes --dry-run` parses the target and prints a JSON target.
- `northstar list-research-runs` prints saved runs.
- invalid theme exits cleanly.

**Step 2: Run tests to verify failure**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_cli.py -q
```

Expected: FAIL because CLI commands do not exist.

**Step 3: Add CLI commands**

Modify `apps/api/src/northstar/cli.py`:

```python
from northstar.research.schemas import ResearchTarget, ResearchTheme
from northstar.research.store import get_research_run, list_research_runs
```

Add:

```python
def _parse_research_themes(values: list[str]) -> list[ResearchTheme]:
  if not values:
    return list(ResearchTheme)

  return [ResearchTheme(value) for value in values]


@app.command("research-city")
def research_city(
    city: str,
    country: str = typer.Option(..., "--country"),
    theme: list[str] = typer.Option([], "--theme"),
    trusted_url: list[str] = typer.Option([], "--trusted-url"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
  """Research a city and prepare RAG notes plus candidate options."""
  try:
    target = ResearchTarget(
      country=country,
      city=city,
      themes=_parse_research_themes(theme),
      trusted_urls=trusted_url,
    )
  except ValueError as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc

  if dry_run:
    typer.echo(json.dumps(target.model_dump(mode="json"), indent=2))
    return

  typer.secho(
    "Research execution is wired in the next task. Use --dry-run for now.",
    fg=typer.colors.YELLOW,
    err=True,
  )
  raise typer.Exit(code=1)


@app.command("list-research-runs")
def list_research_runs_command() -> None:
  try:
    with get_session() as session:
      runs = list_research_runs(session)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps([run.__dict__ for run in runs], indent=2))
```

Wire real execution after Task 6 provides a concrete fetcher and Ollama research agent.

**Step 4: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_cli.py -q
uv run pytest -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/northstar/cli.py apps/api/tests/test_research_cli.py
git commit -m "feat: add research cli commands"
```

---

### Task 6: Candidate Search Tool

**Files:**
- Create: `apps/api/src/northstar/tools/candidates.py`
- Modify: `apps/api/src/northstar/tools/registry.py`
- Test: `apps/api/tests/test_candidate_tool.py`

**Step 1: Write failing tool test**

Create `apps/api/tests/test_candidate_tool.py`:

```python
from northstar.tools.candidates import format_candidate_search_result


def test_format_candidate_search_result_keeps_trust_and_sources() -> None:
  result = format_candidate_search_result(
    candidates=[
      {
        "name": "Quiet Coffee",
        "category": "cafe",
        "area": "Kawaramachi",
        "price_level": "moderate",
        "trust_rating": "medium",
        "source_urls": ["https://example.com"],
        "description": "Central cafe option.",
      }
    ]
  )

  assert result["candidates"][0]["trust_rating"] == "medium"
  assert result["candidates"][0]["source_urls"] == ["https://example.com"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd apps/api
uv run pytest tests/test_candidate_tool.py -q
```

Expected: FAIL because candidate tool does not exist.

**Step 3: Implement candidate tool**

Create `apps/api/src/northstar/tools/candidates.py`:

```python
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from northstar.db import get_session
from northstar.research.schemas import TrustRating
from northstar.research.store import search_candidate_options


def format_candidate_search_result(*, candidates: list[dict[str, Any]]) -> dict[str, Any]:
  return {"candidates": candidates}


def search_candidates(
    country: str,
    city: str,
    category: str | None = None,
    min_trust: str = "medium",
    limit: int = 5,
) -> dict[str, Any]:
  try:
    trust = TrustRating(min_trust)
  except ValueError:
    trust = TrustRating.medium

  try:
    with get_session() as session:
      candidates = search_candidate_options(
        session,
        country=country,
        city=city,
        category=category,
        min_trust=trust,
        limit=limit,
      )
  except SQLAlchemyError:
    return {
      "candidates": [],
      "error": "Candidate database is unavailable.",
    }

  return format_candidate_search_result(
    candidates=[
      {
        "name": candidate.name,
        "category": candidate.category,
        "country": candidate.country,
        "city": candidate.city,
        "area": candidate.area,
        "description": candidate.description,
        "price_level": candidate.price_level,
        "trust_rating": candidate.trust_rating,
        "source_urls": candidate.source_urls,
        "last_checked_at": candidate.last_checked_at,
      }
      for candidate in candidates
    ]
  )
```

Modify `apps/api/src/northstar/tools/registry.py` to add `SEARCH_CANDIDATES_TOOL` and include it in `TOOLS_BY_NAME` and `TOOL_SCHEMAS`.

**Step 4: Run agent tool tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_candidate_tool.py tests/test_agent_loop.py -q
uv run pytest -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/northstar/tools apps/api/tests/test_candidate_tool.py
git commit -m "feat: expose candidate search tool"
```

---

### Task 7: Real Research Agent Prompt Wrapper

**Files:**
- Create: `apps/api/src/northstar/research/agent.py`
- Test: `apps/api/tests/test_research_agent.py`

**Step 1: Write test with fake Ollama client**

Test that `OllamaResearchAgent.research()` calls `structured_chat`, validates the response as `ResearchDraft`, and strips blocked candidates from publishable candidates only at service/store level, not in the raw draft.

**Step 2: Implement wrapper**

Create `apps/api/src/northstar/research/agent.py`:

```python
from northstar.ollama_client import OllamaClient
from northstar.research.schemas import ResearchDraft, ResearchTarget


class ResearchAgentError(RuntimeError):
  pass


class OllamaResearchAgent:
  def __init__(self, *, client: OllamaClient, model: str) -> None:
    self.client = client
    self.model = model

  def research(self, *, target: ResearchTarget, source_texts: list[str]) -> ResearchDraft:
    payload = self.client.structured_chat(
      model=self.model,
      messages=[
        {
          "role": "system",
          "content": (
            "You are Northstar's research agent. Produce stable travel notes "
            "and specific candidate options from source text. Use trust_rating=blocked "
            "for unsupported items. Use price levels, not exact prices."
          ),
        },
        {
          "role": "user",
          "content": (
            f"Target:\n{target.model_dump_json()}\n\n"
            f"Source texts:\n{source_texts[:8]}"
          ),
        },
      ],
      response_format=ResearchDraft.model_json_schema(),
    )
    try:
      return ResearchDraft.model_validate(payload)
    except Exception as exc:
      raise ResearchAgentError("Research agent returned invalid structured output.") from exc
```

**Step 3: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_agent.py -q
uv run pytest -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/src/northstar/research/agent.py apps/api/tests/test_research_agent.py
git commit -m "feat: add ollama research agent"
```

---

### Task 8: Minimal Trusted URL Fetcher

**Files:**
- Create: `apps/api/src/northstar/research/fetcher.py`
- Test: `apps/api/tests/test_research_fetcher.py`

**Step 1: Write tests**

Test:

- `content_hash` is stable for same text.
- HTML is converted to readable text.
- trusted URLs from `ResearchTarget.trusted_urls` are fetched.

Use fake `httpx` transport or pass a callable fetch function. Do not hit the network in tests.

**Step 2: Implement fetcher**

Create `apps/api/src/northstar/research/fetcher.py`:

```python
import hashlib
import re

import httpx

from northstar.research.schemas import ResearchTarget


def hash_text(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def html_to_text(html: str) -> str:
  without_scripts = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
  without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
  return re.sub(r"\s+", " ", without_tags).strip()


class TrustedUrlFetcher:
  def __init__(self, *, timeout: float = 20.0) -> None:
    self.timeout = timeout

  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    texts: list[str] = []

    for url in target.trusted_urls:
      response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
      response.raise_for_status()
      texts.append(html_to_text(response.text))

    return texts
```

This is intentionally not full free-web search yet. It gives us a safe fetcher port and real trusted URL path first. Add open search provider behind the same interface later.

**Step 3: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_fetcher.py -q
uv run pytest -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/src/northstar/research/fetcher.py apps/api/tests/test_research_fetcher.py
git commit -m "feat: fetch trusted research urls"
```

---

### Task 9: Wire Research CLI Execution

**Files:**
- Modify: `apps/api/src/northstar/cli.py`
- Test: `apps/api/tests/test_research_cli.py`

**Step 1: Extend CLI tests**

Add tests that monkeypatch `run_research_pipeline` and verify:

- `research-city Kyoto --country Japan --theme cafes --trusted-url https://example.com` calls the service.
- output includes `run_id`, `status`, candidate count, and validation status.

**Step 2: Wire command**

Modify `research-city` to create:

```python
fetcher = TrustedUrlFetcher()
research_agent = OllamaResearchAgent(client=get_ollama_client(), model=resolved_model)
```

Then call:

```python
result = run_research_pipeline(
  session=session,
  target=target,
  model_name=resolved_model,
  fetcher=fetcher,
  research_agent=research_agent,
  publish_notes=True,
)
```

Catch `OllamaError`, `RuntimeError`, `ValueError`, and `SQLAlchemyError` cleanly.

**Step 3: Run tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_research_cli.py -q
uv run pytest -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/src/northstar/cli.py apps/api/tests/test_research_cli.py
git commit -m "feat: run research pipeline from cli"
```

---

### Task 10: Final Verification

**Files:**
- Modify: `apps/api/README.md`

**Step 1: Document commands**

Add examples:

```bash
uv run northstar research-city Kyoto --country Japan --theme cafes --trusted-url https://kyoto.travel/en/
uv run northstar list-research-runs
```

**Step 2: Run verification**

Run:

```bash
cd apps/api
uv run pytest -q
uv run northstar research-city Kyoto --country Japan --theme cafes --dry-run
```

Expected:

- Tests pass.
- Dry run prints a `ResearchTarget` JSON object.

**Step 3: Commit docs**

```bash
git add apps/api/README.md
git commit -m "docs: document research pipeline commands"
```

---

## Implementation Notes

Do not build the admin dashboard in this branch. Keep the branch focused on backend pipeline primitives.

Do not give the LLM raw SQL or raw database access. The only planner access should be through the `search_candidates` tool.

Do not hardcode a web search provider into the core service. Keep search/fetch behind ports so we can add Brave, Tavily, SerpAPI, or browser-based search later without rewriting the pipeline.

Keep blocked items in research reports, but never publish them to RAG or candidate search.
