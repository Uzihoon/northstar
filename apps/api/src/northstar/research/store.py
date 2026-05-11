from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from northstar.research.models import (
  ResearchCandidateModel,
  ResearchRunModel,
  ResearchSourceSnapshotModel,
)
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
class FetchedSourceSnapshot:
  url: str
  title: str | None
  content_hash: str
  extracted_text: str
  metadata: dict[str, object]
  fetched_at: datetime | None = None


@dataclass(frozen=True)
class SavedSourceSnapshot:
  snapshot_id: str
  run_id: str
  url: str
  title: str | None
  content_hash: str
  extracted_text: str
  fetched_at: str
  metadata: dict[str, object]


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


def _enum_value(value: Enum | str) -> str:
  if isinstance(value, Enum):
    return str(value.value)

  return value


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


def _source_snapshot_from_model(model: ResearchSourceSnapshotModel) -> SavedSourceSnapshot:
  return SavedSourceSnapshot(
    snapshot_id=model.id,
    run_id=model.run_id,
    url=model.url,
    title=model.title,
    content_hash=model.content_hash,
    extracted_text=model.extracted_text,
    fetched_at=model.fetched_at.isoformat(),
    metadata=model.source_metadata or {},
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


def update_research_run_status(
    session: Session,
    *,
    run_id: str,
    status: str,
    report: dict[str, object] | None = None,
) -> SavedResearchRun:
  row = session.get(ResearchRunModel, run_id)
  if row is None:
    raise ValueError(f"Research run not found: {run_id}")

  row.status = status
  row.report = report
  session.commit()
  session.refresh(row)
  return _run_from_model(row)


def list_research_runs(session: Session, *, limit: int = 20) -> list[SavedResearchRun]:
  rows = session.scalars(
    select(ResearchRunModel)
    .order_by(ResearchRunModel.created_at.desc())
    .limit(limit)
  ).all()
  return [_run_from_model(row) for row in rows]


def save_source_snapshots(
    session: Session,
    *,
    run_id: str,
    sources: list[FetchedSourceSnapshot],
) -> list[SavedSourceSnapshot]:
  rows = [
    _source_snapshot_model(run_id=run_id, source=source)
    for source in sources
  ]
  session.add_all(rows)
  session.commit()

  for row in rows:
    session.refresh(row)

  return [_source_snapshot_from_model(row) for row in rows]


def _source_snapshot_model(
    *,
    run_id: str,
    source: FetchedSourceSnapshot,
) -> ResearchSourceSnapshotModel:
  values = {
    "run_id": run_id,
    "url": source.url,
    "title": source.title,
    "content_hash": source.content_hash,
    "extracted_text": source.extracted_text,
    "source_metadata": source.metadata,
  }

  if source.fetched_at is not None:
    values["fetched_at"] = source.fetched_at

  return ResearchSourceSnapshotModel(**values)


def list_source_snapshots(
    session: Session,
    *,
    run_id: str,
) -> list[SavedSourceSnapshot]:
  rows = session.scalars(
    select(ResearchSourceSnapshotModel)
    .where(ResearchSourceSnapshotModel.run_id == run_id)
    .order_by(ResearchSourceSnapshotModel.fetched_at.asc())
  ).all()
  return [_source_snapshot_from_model(row) for row in rows]


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
      category=_enum_value(candidate.category),
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
