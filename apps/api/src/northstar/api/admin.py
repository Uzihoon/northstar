from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from northstar.db import get_session
from northstar.research.store import (
  get_research_run,
  list_research_runs,
  list_source_snapshots,
)


router = APIRouter(prefix="/admin", tags=["admin"])


class AdminResearchRunResponse(BaseModel):
  run_id: str
  target: dict[str, Any]
  model_name: str
  status: str
  report: dict[str, Any] | None = None
  created_at: str
  updated_at: str


class AdminResearchRunListResponse(BaseModel):
  runs: list[AdminResearchRunResponse] = Field(default_factory=list)


class AdminResearchSourceSnapshotResponse(BaseModel):
  snapshot_id: str
  run_id: str
  url: str
  title: str | None = None
  content_hash: str
  fetched_at: str
  query: str | None = None
  source_kind: str | None = None
  trust_hint: str | None = None
  snippet: str = ""
  text_length: int
  text_preview: str


class AdminResearchSourceSnapshotListResponse(BaseModel):
  run_id: str
  sources: list[AdminResearchSourceSnapshotResponse] = Field(default_factory=list)


@router.get("/research/runs", response_model=AdminResearchRunListResponse)
def admin_list_research_runs(limit: int = Query(20, ge=1, le=100)) -> AdminResearchRunListResponse:
  try:
    with get_session() as session:
      runs = list_research_runs(session, limit=limit)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  return AdminResearchRunListResponse(
    runs=[
      AdminResearchRunResponse(
        run_id=run.run_id,
        target=run.target,
        model_name=run.model_name,
        status=run.status,
        report=run.report,
        created_at=run.created_at,
        updated_at=run.updated_at,
      )
      for run in runs
    ],
  )


@router.get("/research/runs/{run_id}", response_model=AdminResearchRunResponse)
def admin_get_research_run(run_id: str) -> AdminResearchRunResponse:
  try:
    with get_session() as session:
      run = get_research_run(session, run_id=run_id)
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  if run is None:
    raise HTTPException(status_code=404, detail="Research run not found.")

  return AdminResearchRunResponse(
    run_id=run.run_id,
    target=run.target,
    model_name=run.model_name,
    status=run.status,
    report=run.report,
    created_at=run.created_at,
    updated_at=run.updated_at,
  )


@router.get(
  "/research/runs/{run_id}/sources",
  response_model=AdminResearchSourceSnapshotListResponse,
)
def admin_list_research_run_sources(
    run_id: str,
    preview_chars: int = Query(500, ge=0, le=5000),
) -> AdminResearchSourceSnapshotListResponse:
  try:
    with get_session() as session:
      run = get_research_run(session, run_id=run_id)
      if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")

      snapshots = list_source_snapshots(session, run_id=run_id)
  except HTTPException:
    raise
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc

  return AdminResearchSourceSnapshotListResponse(
    run_id=run_id,
    sources=[
      _source_snapshot_response(snapshot=snapshot, preview_chars=preview_chars)
      for snapshot in snapshots
    ],
  )


def _source_snapshot_response(
    *,
    snapshot,
    preview_chars: int,
) -> AdminResearchSourceSnapshotResponse:
  metadata = snapshot.metadata or {}
  extracted_text = snapshot.extracted_text or ""

  return AdminResearchSourceSnapshotResponse(
    snapshot_id=snapshot.snapshot_id,
    run_id=snapshot.run_id,
    url=snapshot.url,
    title=snapshot.title,
    content_hash=snapshot.content_hash,
    fetched_at=snapshot.fetched_at,
    query=_metadata_string(metadata, "query"),
    source_kind=_metadata_string(metadata, "source_kind"),
    trust_hint=_metadata_string(metadata, "trust_hint"),
    snippet=_metadata_string(metadata, "snippet") or "",
    text_length=len(extracted_text),
    text_preview=extracted_text[:preview_chars],
  )


def _metadata_string(metadata: dict[str, object], key: str) -> str | None:
  value = metadata.get(key)

  if isinstance(value, str):
    return value

  return None
