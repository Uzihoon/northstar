from dataclasses import dataclass

from northstar.research.schemas import TrustRating
from northstar.tools.candidates import format_candidate_search_result, search_candidates
from northstar.tools.registry import TOOL_SCHEMAS, TOOLS_BY_NAME


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


@dataclass(frozen=True)
class FakeCandidate:
  candidate_id: str = "candidate-1"
  run_id: str = "run-1"
  name: str = "Quiet Coffee"
  category: str = "cafe"
  country: str = "Japan"
  city: str = "Kyoto"
  area: str | None = "Kawaramachi"
  description: str = "Central cafe option."
  price_level: str = "moderate"
  trust_rating: str = "medium"
  source_urls: list[str] = None
  last_checked_at: str = "2026-05-09T10:00:00+00:00"
  metadata: dict[str, object] = None

  def __post_init__(self) -> None:
    if self.source_urls is None:
      object.__setattr__(self, "source_urls", ["https://example.com"])
    if self.metadata is None:
      object.__setattr__(self, "metadata", {})


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


def test_search_candidates_queries_store_and_formats_results(monkeypatch) -> None:
  captured = {}

  def fake_search_candidate_options(**kwargs):
    captured.update(kwargs)
    return [FakeCandidate()]

  monkeypatch.setattr("northstar.tools.candidates.get_session", lambda: FakeSession())
  monkeypatch.setattr(
    "northstar.tools.candidates.search_candidate_options",
    fake_search_candidate_options,
  )

  result = search_candidates(
    country="Japan",
    city="Kyoto",
    category="cafe",
    min_trust="medium",
    limit=3,
  )

  assert captured["country"] == "Japan"
  assert captured["city"] == "Kyoto"
  assert captured["category"] == "cafe"
  assert captured["min_trust"] == TrustRating.medium
  assert captured["limit"] == 3
  assert result["candidates"][0]["name"] == "Quiet Coffee"
  assert result["candidates"][0]["source_urls"] == ["https://example.com"]


def test_search_candidates_tool_is_registered_for_agent_use() -> None:
  assert "search_candidates" in TOOLS_BY_NAME
  assert any(
    schema["function"]["name"] == "search_candidates"
    for schema in TOOL_SCHEMAS
  )
