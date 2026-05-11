from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field

from northstar.research.schemas import ResearchTarget, TrustRating


TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


class SourceSearchResult(BaseModel):
  title: str
  url: str
  snippet: str = ""


class DiscoveredSource(BaseModel):
  title: str
  url: str
  snippet: str = ""
  query: str | None = None
  source_kind: str
  trust_hint: TrustRating
  rank: int = Field(default=0, exclude=True)


class SourceSearchClient(Protocol):
  def search(self, *, query: str, limit: int) -> list[SourceSearchResult]:
    ...


def normalize_source_url(url: str) -> str:
  parsed = urlsplit(url)
  query_items = [
    (key, value)
    for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    if key not in TRACKING_QUERY_KEYS
    and not any(key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES)
  ]
  cleaned_query = urlencode(query_items, doseq=True)
  return urlunsplit((
    parsed.scheme.lower(),
    parsed.netloc.lower(),
    parsed.path,
    cleaned_query,
    "",
  ))


def build_source_queries(target: ResearchTarget) -> list[str]:
  queries: list[str] = []

  for theme in target.themes:
    topic = theme.value
    queries.extend([
      f"{target.city} {target.country} official travel {topic}",
      f"{target.city} {target.country} {topic} guide",
    ])

  return _unique_strings(queries)


def build_seed_sources(target: ResearchTarget) -> list[DiscoveredSource]:
  return [
    DiscoveredSource(
      title=url,
      url=normalize_source_url(url),
      snippet="Operator supplied trusted URL.",
      query=None,
      source_kind="trusted_url",
      trust_hint=TrustRating.high,
      rank=index,
    )
    for index, url in enumerate(target.trusted_urls)
  ]


def discover_sources(
    *,
    target: ResearchTarget,
    search_client: SourceSearchClient,
    max_results_per_query: int = 5,
    max_sources: int = 12,
) -> list[DiscoveredSource]:
  sources_by_url: dict[str, DiscoveredSource] = {}

  for source in build_seed_sources(target):
    sources_by_url[source.url] = source

  rank = len(sources_by_url)

  for query in build_source_queries(target):
    for result in search_client.search(query=query, limit=max_results_per_query):
      url = normalize_source_url(result.url)

      if url in sources_by_url:
        continue

      sources_by_url[url] = DiscoveredSource(
        title=result.title,
        url=url,
        snippet=result.snippet,
        query=query,
        source_kind="search_result",
        trust_hint=TrustRating.low,
        rank=rank,
      )
      rank += 1

  return sorted(
    sources_by_url.values(),
    key=lambda source: (_trust_rank(source), source.rank),
  )[:max_sources]


def _trust_rank(source: DiscoveredSource) -> int:
  source_kind_rank = 0 if source.source_kind == "trusted_url" else 1
  trust_rank = {
    TrustRating.high: 0,
    TrustRating.medium: 1,
    TrustRating.low: 2,
    TrustRating.blocked: 3,
  }[source.trust_hint]
  return source_kind_rank + trust_rank


def _unique_strings(values: list[str]) -> list[str]:
  seen: set[str] = set()
  unique: list[str] = []

  for value in values:
    if value in seen:
      continue

    seen.add(value)
    unique.append(value)

  return unique
