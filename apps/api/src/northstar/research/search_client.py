from typing import Any, Callable, Protocol

import httpx

from northstar.research.discovery import SourceSearchResult


BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class SearchConfigurationError(RuntimeError):
  """Raised when web search is requested without usable configuration."""


class SearchResponse(Protocol):
  def raise_for_status(self) -> None:
    ...

  def json(self) -> dict[str, Any]:
    ...


SearchGet = Callable[..., SearchResponse]
SearchPost = Callable[..., SearchResponse]


class BraveSearchClient:
  def __init__(
      self,
      *,
      api_key: str,
      get: SearchGet | None = None,
      timeout: float = 20.0,
      country: str = "us",
      search_lang: str = "en",
  ) -> None:
    self.api_key = api_key
    self.get = get or httpx.get
    self.timeout = timeout
    self.country = country
    self.search_lang = search_lang

  def search(self, *, query: str, limit: int) -> list[SourceSearchResult]:
    response = self.get(
      BRAVE_WEB_SEARCH_URL,
      headers={
        "Accept": "application/json",
        "X-Subscription-Token": self.api_key,
      },
      params={
        "q": query,
        "count": limit,
        "country": self.country,
        "search_lang": self.search_lang,
      },
      timeout=self.timeout,
    )
    response.raise_for_status()
    payload = response.json()
    web_results = payload.get("web", {}).get("results", [])

    return [
      SourceSearchResult(
        title=str(result.get("title") or ""),
        url=str(result.get("url") or ""),
        snippet=str(result.get("description") or ""),
      )
      for result in web_results
      if isinstance(result, dict) and result.get("url")
    ]


class TavilySearchClient:
  def __init__(
      self,
      *,
      api_key: str,
      post: SearchPost | None = None,
      timeout: float = 20.0,
      search_depth: str = "basic",
      country: str | None = None,
  ) -> None:
    self.api_key = api_key
    self.post = post or httpx.post
    self.timeout = timeout
    self.search_depth = search_depth
    self.country = country

  def search(self, *, query: str, limit: int) -> list[SourceSearchResult]:
    body: dict[str, object] = {
      "query": query,
      "max_results": limit,
      "search_depth": self.search_depth,
      "topic": "general",
      "include_answer": False,
      "include_raw_content": False,
    }

    if self.country:
      body["country"] = self.country

    response = self.post(
      TAVILY_SEARCH_URL,
      headers={
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
      },
      json=body,
      timeout=self.timeout,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])

    return [
      SourceSearchResult(
        title=str(result.get("title") or ""),
        url=str(result.get("url") or ""),
        snippet=str(result.get("content") or ""),
      )
      for result in results
      if isinstance(result, dict) and result.get("url")
    ]


def build_source_search_client(settings: object) -> BraveSearchClient | TavilySearchClient | None:
  provider = str(getattr(settings, "search_provider", "none")).strip().lower()

  if provider in {"", "none"}:
    return None

  if provider == "brave":
    api_key = getattr(settings, "brave_search_api_key", None)
    if not api_key:
      raise SearchConfigurationError(
        "BRAVE_SEARCH_API_KEY is required when SEARCH_PROVIDER=brave."
      )

    return BraveSearchClient(
      api_key=str(api_key),
      country=str(getattr(settings, "brave_search_country", "us")),
      search_lang=str(getattr(settings, "brave_search_lang", "en")),
    )

  if provider == "tavily":
    api_key = getattr(settings, "tavily_api_key", None)
    if not api_key:
      raise SearchConfigurationError(
        "TAVILY_API_KEY is required when SEARCH_PROVIDER=tavily."
      )

    return TavilySearchClient(
      api_key=str(api_key),
      search_depth=str(getattr(settings, "tavily_search_depth", "basic")),
      country=getattr(settings, "tavily_country", None),
    )

  raise SearchConfigurationError(
    f"Unsupported SEARCH_PROVIDER: {provider}. Supported providers: brave, tavily"
  )
