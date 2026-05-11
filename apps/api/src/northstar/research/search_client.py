from typing import Any, Callable, Protocol

import httpx

from northstar.research.discovery import SourceSearchResult


BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class SearchConfigurationError(RuntimeError):
  """Raised when web search is requested without usable configuration."""


class SearchResponse(Protocol):
  def raise_for_status(self) -> None:
    ...

  def json(self) -> dict[str, Any]:
    ...


SearchGet = Callable[..., SearchResponse]


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
        title=str(result.get("title", "")),
        url=str(result.get("url", "")),
        snippet=str(result.get("description", "")),
      )
      for result in web_results
      if isinstance(result, dict) and result.get("url")
    ]


def build_source_search_client(settings: object) -> BraveSearchClient | None:
  provider = str(getattr(settings, "search_provider", "none")).lower()

  if provider in {"", "none"}:
    return None

  if provider != "brave":
    raise SearchConfigurationError(
      f"Unsupported SEARCH_PROVIDER: {provider}. Supported providers: brave"
    )

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
