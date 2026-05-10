from northstar.research.fetcher import TrustedUrlFetcher, hash_text, html_to_text
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
