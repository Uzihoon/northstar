from northstar.research.discovery import (
  SourceSearchResult,
  build_source_queries,
  discover_sources,
  normalize_source_url,
)
from northstar.research.schemas import ResearchTarget, ResearchTheme, TrustRating


class FakeSearchClient:
  def __init__(self) -> None:
    self.calls: list[dict[str, object]] = []

  def search(self, *, query: str, limit: int) -> list[SourceSearchResult]:
    self.calls.append({"query": query, "limit": limit})
    return [
      SourceSearchResult(
        title="Duplicate official source",
        url="https://kyoto.travel/en/#top",
        snippet="Official Kyoto travel guide.",
      ),
      SourceSearchResult(
        title="Quiet cafe roundup",
        url="https://example.com/kyoto-cafes?utm_source=newsletter",
        snippet="Independent cafe list.",
      ),
    ]


def test_build_source_queries_covers_themes_with_official_query_first() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes, ResearchTheme.accommodation],
  )

  queries = build_source_queries(target)

  assert queries[:4] == [
    "Kyoto Japan official travel cafes",
    "Kyoto Japan cafes guide",
    "Kyoto Japan official travel accommodation",
    "Kyoto Japan accommodation guide",
  ]
  assert len(queries) == len(set(queries))


def test_normalize_source_url_removes_fragments_and_tracking_params() -> None:
  assert (
    normalize_source_url("https://example.com/guide?utm_source=email&ref=planner#section")
    == "https://example.com/guide?ref=planner"
  )


def test_discover_sources_prioritizes_trusted_urls_and_deduplicates_results() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
    trusted_urls=["https://kyoto.travel/en/"],
  )
  search_client = FakeSearchClient()

  sources = discover_sources(
    target=target,
    search_client=search_client,
    max_results_per_query=2,
    max_sources=3,
  )

  assert [source.url for source in sources] == [
    "https://kyoto.travel/en/",
    "https://example.com/kyoto-cafes",
  ]
  assert sources[0].source_kind == "trusted_url"
  assert sources[0].trust_hint == TrustRating.high
  assert sources[1].source_kind == "search_result"
  assert search_client.calls == [
    {"query": "Kyoto Japan official travel cafes", "limit": 2},
    {"query": "Kyoto Japan cafes guide", "limit": 2},
  ]
