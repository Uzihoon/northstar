from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from northstar.db import Base

def utc_now() -> datetime:
  return datetime.now(timezone.utc)

class RagChunkModel(Base):
  __tablename__ = "rag_chunks"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  source_path: Mapped[str] = mapped_column(Text)
  chunk_index: Mapped[int] = mapped_column()
  text: Mapped[str] = mapped_column(Text)
  chunk_metadata: Mapped[dict[str, object]] = mapped_column(JSON)
  embedding: Mapped[list[float]] = mapped_column(Vector(1024))
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
