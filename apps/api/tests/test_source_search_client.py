from types import SimpleNamespace

import httpx
import pytest

from northstar.research.discovery import SourceSearchResult
from northstar.research.search_client import (
  BraveSearchClient,
  SearchConfigurationError,
  TavilySearchClient,
  build_source_search_client,
)


class FakeResponse:
  def __init__(self, payload: dict[str, object]) -> None:
    self.payload = payload
    self.raise_for_status_called = False

  def raise_for_status(self) -> None:
    self.raise_for_status_called = True

  def json(self) -> dict[str, object]:
    return self.payload


class FakeFailedResponse:
  def __init__(self, *, status_code: int, text: str) -> None:
    self.status_code = status_code
    self.text = text
    self.reason_phrase = "Bad Request"
    self.request = httpx.Request("POST", "https://api.tavily.com/search")

  def raise_for_status(self) -> None:
    raise httpx.HTTPStatusError(
      "Client error '400 Bad Request'",
      request=self.request,
      response=httpx.Response(
        self.status_code,
        text=self.text,
        request=self.request,
      ),
    )

  def json(self) -> dict[str, object]:
    return {}


def test_brave_search_client_maps_web_results() -> None:
  calls: list[dict[str, object]] = []
  response = FakeResponse({
    "web": {
      "results": [
        {
          "title": "Kyoto Official Travel",
          "url": "https://kyoto.travel/en/",
          "description": "Official Kyoto tourism guide.",
        },
        {
          "title": "Quiet Cafes",
          "url": "https://example.com/cafes",
          "description": "Independent cafe guide.",
        },
      ]
    }
  })

  def fake_get(url: str, **kwargs):
    calls.append({"url": url, **kwargs})
    return response

  client = BraveSearchClient(
    api_key="secret",
    get=fake_get,
    timeout=7.0,
    country="us",
    search_lang="en",
  )

  results = client.search(query="Kyoto Japan cafes", limit=2)

  assert results == [
    SourceSearchResult(
      title="Kyoto Official Travel",
      url="https://kyoto.travel/en/",
      snippet="Official Kyoto tourism guide.",
    ),
    SourceSearchResult(
      title="Quiet Cafes",
      url="https://example.com/cafes",
      snippet="Independent cafe guide.",
    ),
  ]
  assert response.raise_for_status_called is True
  assert calls == [
    {
      "url": "https://api.search.brave.com/res/v1/web/search",
      "headers": {
        "Accept": "application/json",
        "X-Subscription-Token": "secret",
      },
      "params": {
        "q": "Kyoto Japan cafes",
        "count": 2,
        "country": "us",
        "search_lang": "en",
      },
      "timeout": 7.0,
    }
  ]


def test_build_source_search_client_requires_brave_key() -> None:
  settings = SimpleNamespace(
    search_provider="brave",
    brave_search_api_key=None,
    brave_search_country="us",
    brave_search_lang="en",
  )

  with pytest.raises(SearchConfigurationError, match="BRAVE_SEARCH_API_KEY"):
    build_source_search_client(settings)


def test_tavily_search_client_maps_results() -> None:
  calls: list[dict[str, object]] = []
  response = FakeResponse({
    "results": [
      {
        "title": "Kyoto Cafes",
        "url": "https://example.com/kyoto-cafes",
        "content": "A focused cafe guide for Kyoto.",
      }
    ]
  })

  def fake_post(url: str, **kwargs):
    calls.append({"url": url, **kwargs})
    return response

  client = TavilySearchClient(
    api_key="tvly-secret",
    post=fake_post,
    timeout=8.0,
    search_depth="basic",
  )

  results = client.search(query="Kyoto Japan cafes", limit=3)

  assert results == [
    SourceSearchResult(
      title="Kyoto Cafes",
      url="https://example.com/kyoto-cafes",
      snippet="A focused cafe guide for Kyoto.",
    )
  ]
  assert response.raise_for_status_called is True
  assert calls == [
    {
      "url": "https://api.tavily.com/search",
      "headers": {
        "Authorization": "Bearer tvly-secret",
        "Content-Type": "application/json",
      },
      "json": {
        "query": "Kyoto Japan cafes",
        "max_results": 3,
        "search_depth": "basic",
        "topic": "general",
        "include_answer": False,
        "include_raw_content": False,
      },
      "timeout": 8.0,
    }
  ]


def test_tavily_search_client_includes_error_body_for_bad_requests() -> None:
  def fake_post(url: str, **kwargs):
    return FakeFailedResponse(
      status_code=400,
      text='{"detail":"country must be a valid enum value"}',
    )

  client = TavilySearchClient(
    api_key="tvly-secret",
    post=fake_post,
    search_depth="basic",
  )

  with pytest.raises(httpx.HTTPStatusError, match="country must be a valid enum value"):
    client.search(query="Seoul South Korea cafes", limit=3)


def test_build_source_search_client_returns_tavily_client() -> None:
  settings = SimpleNamespace(
    search_provider="tavily",
    tavily_api_key="tvly-secret",
    tavily_search_depth="basic",
  )

  client = build_source_search_client(settings)

  assert isinstance(client, TavilySearchClient)


def test_build_source_search_client_ignores_obsolete_tavily_country_setting() -> None:
  settings = SimpleNamespace(
    search_provider="tavily",
    tavily_api_key="tvly-secret",
    tavily_search_depth="basic",
    tavily_country="japan",
  )

  client = build_source_search_client(settings)

  assert not hasattr(client, "country")


def test_build_source_search_client_requires_tavily_key() -> None:
  settings = SimpleNamespace(
    search_provider="tavily",
    tavily_api_key=None,
    tavily_search_depth="basic",
  )

  with pytest.raises(SearchConfigurationError, match="TAVILY_API_KEY"):
    build_source_search_client(settings)
