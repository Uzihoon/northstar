from types import SimpleNamespace

import pytest

from northstar.research.discovery import SourceSearchResult
from northstar.research.search_client import (
  BraveSearchClient,
  SearchConfigurationError,
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
