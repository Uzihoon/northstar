from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from northstar.db import get_session
from northstar.research.schemas import TrustRating
from northstar.research.store import SavedCandidateOption, search_candidate_options


def _candidate_to_dict(candidate: SavedCandidateOption) -> dict[str, Any]:
  return {
    "candidate_id": candidate.candidate_id,
    "run_id": candidate.run_id,
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
    "metadata": candidate.metadata,
  }


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
        session=session,
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
      _candidate_to_dict(candidate)
      for candidate in candidates
    ]
  )
