from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from northstar.db import Base

def utc_now() -> datetime:
  return datetime.now(timezone.utc)

class User(Base):
  __tablename__ = "users"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  profile: Mapped[UserPreferenceProfileModel | None] = relationship(
    back_populates="user", uselist=False, cascade="all, delete-orphan"
  )
  preference_updates: Mapped[list[PreferenceUpdateModel]] = relationship(
    back_populates="user", cascade="all, delete-orphan"
  )

class UserPreferenceProfileModel(Base):
  __tablename__ = "user_preference_profiles"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
  pace: Mapped[str | None] = mapped_column(String(32), nullable=True)
  budget_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
  interests: Mapped[list[str]] = mapped_column(JSON, default=list)
  food_preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
  dislikes: Mapped[list[str]] = mapped_column(JSON, default=list)
  notes: Mapped[list[str]] = mapped_column(JSON, default=list)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

  user: Mapped[User] = relationship(back_populates="profile")

class PreferenceUpdateModel(Base):
  __tablename__ = "preference_updates"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
  source_kind: Mapped[str] = mapped_column(String(32))
  source_text: Mapped[str] = mapped_column(Text)
  candidate: Mapped[dict[str, object]] = mapped_column(JSON)
  applied_patch: Mapped[dict[str, object]] = mapped_column(JSON)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  user: Mapped[User] = relationship(back_populates="preference_updates")

class TripRequestModel(Base):
  __tablename__ = "trip_requests"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
  original_prompt: Mapped[str] = mapped_column(Text)
  extracted_request: Mapped[dict[str, object]] = mapped_column(JSON)
  active_context: Mapped[dict[str, object]] = mapped_column(JSON)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  user: Mapped[User] = relationship()
  plans: Mapped[list["ItineraryPlanModel"]] = relationship(
    back_populates="trip_request", cascade="all, delete-orphan"
  )

class ItineraryPlanModel(Base):
  __tablename__ = "itinerary_plans"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default= lambda: str(uuid.uuid4()))
  trip_request_id: Mapped[str] = mapped_column(ForeignKey("trip_requests.id"), index=True)
  model_name: Mapped[str] = mapped_column(String(128))
  itinerary: Mapped[dict[str, object]] = mapped_column(JSON)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  trip_request: Mapped[TripRequestModel] = relationship(back_populates="plans")

class EvalRunModel(Base):
  __tablename__ = "eval_runs"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  suite: Mapped[str] = mapped_column(String(64), index=True)
  model_name: Mapped[str] = mapped_column(String(128))
  passed: Mapped[int] = mapped_column()
  failed: Mapped[int] = mapped_column()
  total: Mapped[int] = mapped_column()
  pass_rate: Mapped[float] = mapped_column()
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

  case_results: Mapped[list["EvalCaseResultModel"]] = relationship(
    back_populates="eval_run", cascade="all, delete-orphan"
  )

class EvalCaseResultModel(Base):
  __tablename__ = "eval_case_results"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  eval_run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id"), index=True)
  case_id: Mapped[str] = mapped_column(String(128))
  passed: Mapped[bool] = mapped_column()
  checks: Mapped[list[dict[str, object]]] = mapped_column(JSON)

  eval_run: Mapped[EvalRunModel] = relationship(back_populates="case_results")