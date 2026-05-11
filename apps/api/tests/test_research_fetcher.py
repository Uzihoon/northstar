from northstar.research.discovery import SourceSearchResult
from northstar.research.fetcher import (
  DiscoveryUrlFetcher,
  TrustedUrlFetcher,
  hash_text,
  html_to_text,
)
from northstar.research.schemas import ResearchTarget, ResearchTheme


class FakeResponse:
  def __init__(self, text: str) -> None:
    self.text = text
    self.raise_for_status_called = False

  def raise_for_status(self) -> None:
    self.raise_for_status_called = True


def test_hash_text_is_stable_for_same_text() -> None:
  assert hash_text("Kyoto cafe notes") == hash_text("Kyoto cafe notes")
  assert hash_text("Kyoto cafe notes") != hash_text("Kyoto transport notes")


def test_html_to_text_removes_scripts_styles_tags_and_unescapes_entities() -> None:
  html = """
  <html>
    <head>
      <style>.hidden { display: none; }</style>
      <script>alert("nope")</script>
    </head>
    <body>
      <h1>Kyoto Cafes</h1>
      <p>Quiet coffee &amp; scenic walks.</p>
    </body>
  </html>
  """

  text = html_to_text(html)

  assert text == "Kyoto Cafes Quiet coffee & scenic walks."


def test_trusted_url_fetcher_fetches_target_trusted_urls() -> None:
  calls: list[dict[str, object]] = []
  responses = [
    FakeResponse("<h1>Kyoto Official Travel</h1>"),
    FakeResponse("<p>Cafe guide text.</p>"),
  ]

  def fake_get(url: str, **kwargs):
    calls.append({"url": url, **kwargs})
    return responses.pop(0)

  fetcher = TrustedUrlFetcher(get=fake_get, timeout=12.0)

  texts = fetcher.fetch_texts(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
      trusted_urls=[
        "https://kyoto.travel/en/",
        "https://example.com/cafes",
      ],
    )
  )

  assert texts == [
    "Kyoto Official Travel",
    "Cafe guide text.",
  ]
  assert calls == [
    {
      "url": "https://kyoto.travel/en/",
      "timeout": 12.0,
      "follow_redirects": True,
    },
    {
      "url": "https://example.com/cafes",
      "timeout": 12.0,
      "follow_redirects": True,
    },
  ]


def test_trusted_url_fetcher_returns_source_documents() -> None:
  response = FakeResponse("<h1>Kyoto Official Travel</h1>")

  def fake_get(url: str, **kwargs):
    return response

  fetcher = TrustedUrlFetcher(get=fake_get, timeout=12.0)

  documents = fetcher.fetch_documents(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
      trusted_urls=["https://kyoto.travel/en/#top"],
    )
  )

  assert len(documents) == 1
  assert documents[0].url == "https://kyoto.travel/en/"
  assert documents[0].title == "https://kyoto.travel/en/"
  assert documents[0].source_kind == "trusted_url"
  assert documents[0].trust_hint == "high"
  assert documents[0].text == "Kyoto Official Travel"
  assert documents[0].content_hash == hash_text("Kyoto Official Travel")


def test_discovery_url_fetcher_fetches_trusted_and_discovered_urls() -> None:
  search_calls: list[dict[str, object]] = []
  get_calls: list[dict[str, object]] = []
  responses = [
    FakeResponse("<h1>Kyoto Official Travel</h1>"),
    FakeResponse("<p>Independent cafe guide.</p>"),
  ]

  class FakeSearchClient:
    def search(self, *, query: str, limit: int) -> list[SourceSearchResult]:
      search_calls.append({"query": query, "limit": limit})
      return [
        SourceSearchResult(
          title="Independent cafe guide",
          url="https://example.com/cafes?utm_source=test",
          snippet="Cafe notes.",
        )
      ]

  def fake_get(url: str, **kwargs):
    get_calls.append({"url": url, **kwargs})
    return responses.pop(0)

  fetcher = DiscoveryUrlFetcher(
    search_client=FakeSearchClient(),
    get=fake_get,
    timeout=9.0,
    max_results_per_query=1,
    max_sources=2,
  )

  texts = fetcher.fetch_texts(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
      trusted_urls=["https://kyoto.travel/en/"],
    )
  )

  assert texts == [
    "Kyoto Official Travel",
    "Independent cafe guide.",
  ]
  assert search_calls == [
    {"query": "Kyoto Japan official travel cafes", "limit": 1},
    {"query": "Kyoto Japan cafes guide", "limit": 1},
  ]
  assert get_calls == [
    {
      "url": "https://kyoto.travel/en/",
      "timeout": 9.0,
      "follow_redirects": True,
    },
    {
      "url": "https://example.com/cafes",
      "timeout": 9.0,
      "follow_redirects": True,
    },
  ]


def test_discovery_url_fetcher_preserves_discovered_source_metadata() -> None:
  responses = [
    FakeResponse("<h1>Kyoto Official Travel</h1>"),
    FakeResponse("<p>Independent cafe guide.</p>"),
  ]

  class FakeSearchClient:
    def search(self, *, query: str, limit: int) -> list[SourceSearchResult]:
      return [
        SourceSearchResult(
          title="Independent cafe guide",
          url="https://example.com/cafes?utm_source=test",
          snippet="Cafe notes.",
        )
      ]

  def fake_get(url: str, **kwargs):
    return responses.pop(0)

  fetcher = DiscoveryUrlFetcher(
    search_client=FakeSearchClient(),
    get=fake_get,
    max_results_per_query=1,
    max_sources=2,
  )

  documents = fetcher.fetch_documents(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
      trusted_urls=["https://kyoto.travel/en/"],
    )
  )

  assert [
    {
      "url": document.url,
      "title": document.title,
      "query": document.query,
      "source_kind": document.source_kind,
      "trust_hint": document.trust_hint,
      "snippet": document.snippet,
    }
    for document in documents
  ] == [
    {
      "url": "https://kyoto.travel/en/",
      "title": "https://kyoto.travel/en/",
      "query": None,
      "source_kind": "trusted_url",
      "trust_hint": "high",
      "snippet": "Operator supplied trusted URL.",
    },
    {
      "url": "https://example.com/cafes",
      "title": "Independent cafe guide",
      "query": "Kyoto Japan official travel cafes",
      "source_kind": "search_result",
      "trust_hint": "low",
      "snippet": "Cafe notes.",
    },
  ]
