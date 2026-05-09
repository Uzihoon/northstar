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
