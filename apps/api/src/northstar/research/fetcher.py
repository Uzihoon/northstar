import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

import httpx

from northstar.research.discovery import (
  DiscoveredSource,
  SourceSearchClient,
  build_seed_sources,
  discover_sources,
)
from northstar.research.schemas import ResearchTarget


class FetchResponse(Protocol):
  text: str

  def raise_for_status(self) -> None:
    ...


FetchGet = Callable[..., FetchResponse]


@dataclass(frozen=True)
class FetchedSourceDocument:
  url: str
  title: str | None
  text: str
  content_hash: str
  query: str | None = None
  source_kind: str = "trusted_url"
  trust_hint: str | None = None
  snippet: str = ""
  fetched_at: datetime | None = None


@dataclass(frozen=True)
class SourceFetchFailure:
  url: str
  title: str | None
  error: str
  query: str | None = None
  source_kind: str = "trusted_url"
  trust_hint: str | None = None
  snippet: str = ""
  fetched_at: datetime | None = None


def hash_text(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def html_to_text(raw_html: str) -> str:
  without_scripts = re.sub(
    r"<(script|style)\b[^>]*>.*?</\1>",
    " ",
    raw_html,
    flags=re.DOTALL | re.IGNORECASE,
  )
  without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
  unescaped = html.unescape(without_tags)
  return re.sub(r"\s+", " ", unescaped).strip()


class TrustedUrlFetcher:
  def __init__(
      self,
      *,
      timeout: float = 20.0,
      get: FetchGet | None = None,
  ) -> None:
    self.timeout = timeout
    self.get = get or httpx.get
    self.fetch_failures: list[SourceFetchFailure] = []

  def fetch_documents(self, *, target: ResearchTarget) -> list[FetchedSourceDocument]:
    self.fetch_failures = []
    documents: list[FetchedSourceDocument] = []

    for source in build_seed_sources(target):
      document = self._fetch_source(source)
      if document is None:
        continue

      documents.append(document)

    return documents

  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    return [
      document.text
      for document in self.fetch_documents(target=target)
    ]

  def _fetch_source(self, source: DiscoveredSource) -> FetchedSourceDocument | None:
    try:
      response = self.get(
        source.url,
        timeout=self.timeout,
        follow_redirects=True,
      )
      response.raise_for_status()
    except httpx.HTTPError as exc:
      self.fetch_failures.append(_fetch_failure_from_exception(source, exc))
      return None

    text = html_to_text(response.text)

    return FetchedSourceDocument(
      url=source.url,
      title=source.title,
      text=text,
      content_hash=hash_text(text),
      query=source.query,
      source_kind=source.source_kind,
      trust_hint=source.trust_hint.value,
      snippet=source.snippet,
      fetched_at=datetime.now(timezone.utc),
    )


class DiscoveryUrlFetcher:
  def __init__(
      self,
      *,
      search_client: SourceSearchClient,
      timeout: float = 20.0,
      get: FetchGet | None = None,
      max_results_per_query: int = 5,
      max_sources: int = 12,
  ) -> None:
    self.search_client = search_client
    self.timeout = timeout
    self.get = get or httpx.get
    self.max_results_per_query = max_results_per_query
    self.max_sources = max_sources
    self.fetch_failures: list[SourceFetchFailure] = []

  def fetch_documents(self, *, target: ResearchTarget) -> list[FetchedSourceDocument]:
    sources = discover_sources(
      target=target,
      search_client=self.search_client,
      max_results_per_query=self.max_results_per_query,
      max_sources=self.max_sources,
    )
    trusted_fetcher = TrustedUrlFetcher(
      timeout=self.timeout,
      get=self.get,
    )
    documents: list[FetchedSourceDocument] = []

    for source in sources:
      document = trusted_fetcher._fetch_source(source)
      if document is None:
        continue

      documents.append(document)

    self.fetch_failures = trusted_fetcher.fetch_failures
    return documents

  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    return [
      document.text
    for document in self.fetch_documents(target=target)
  ]


def _fetch_failure_from_exception(
    source: DiscoveredSource,
    exc: httpx.HTTPError,
) -> SourceFetchFailure:
  status_code = None
  if isinstance(exc, httpx.HTTPStatusError):
    status_code = exc.response.status_code

  message = str(exc)
  if status_code is not None and str(status_code) not in message:
    message = f"{message} ({status_code})"

  return SourceFetchFailure(
    url=source.url,
    title=source.title,
    error=message,
    query=source.query,
    source_kind=source.source_kind,
    trust_hint=source.trust_hint.value,
    snippet=source.snippet,
    fetched_at=datetime.now(timezone.utc),
  )
