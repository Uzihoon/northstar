import json
from dataclasses import dataclass
from types import SimpleNamespace

from typer.testing import CliRunner

import northstar.cli as cli_module
from northstar.research.schemas import ResearchValidationReport


runner = CliRunner()


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


@dataclass(frozen=True)
class FakeResearchRun:
  run_id: str
  target: dict[str, object]
  model_name: str
  status: str
  report: dict[str, object] | None
  created_at: str
  updated_at: str


def test_research_city_dry_run_prints_target() -> None:
  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--trusted-url",
      "https://kyoto.travel/en/",
      "--dry-run",
    ],
  )

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload == {
    "country": "Japan",
    "city": "Kyoto",
    "themes": ["cafes"],
    "trusted_urls": ["https://kyoto.travel/en/"],
  }


def test_research_city_rejects_invalid_theme() -> None:
  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "nightlife",
      "--dry-run",
    ],
  )

  assert result.exit_code == 1
  assert "Invalid research theme: nightlife" in result.stderr


def test_plan_research_sources_prints_query_plan() -> None:
  result = runner.invoke(
    cli_module.app,
    [
      "plan-research-sources",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--trusted-url",
      "https://kyoto.travel/en/",
    ],
  )

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload == {
    "target": {
      "country": "Japan",
      "city": "Kyoto",
      "themes": ["cafes"],
      "trusted_urls": ["https://kyoto.travel/en/"],
    },
    "queries": [
      "Kyoto Japan official travel cafes",
      "Kyoto Japan cafes guide",
    ],
    "seed_sources": [
      {
        "title": "https://kyoto.travel/en/",
        "url": "https://kyoto.travel/en/",
        "snippet": "Operator supplied trusted URL.",
        "query": None,
        "source_kind": "trusted_url",
        "trust_hint": "high",
      }
    ],
  }


def test_discover_research_sources_prints_search_results(monkeypatch) -> None:
  class FakeSettings:
    search_provider = "tavily"
    tavily_api_key = "secret"
    tavily_search_depth = "basic"
    tavily_country = "japan"

  class FakeSearchClient:
    def search(self, *, query: str, limit: int):
      return [
        cli_module.SourceSearchResult(
          title="Kyoto Cafes",
          url="https://example.com/cafes?utm_source=test",
          snippet="Cafe guide.",
        )
      ]

  monkeypatch.setattr(cli_module, "get_settings", lambda: FakeSettings())
  monkeypatch.setattr(cli_module, "build_source_search_client", lambda settings: FakeSearchClient())

  result = runner.invoke(
    cli_module.app,
    [
      "discover-research-sources",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--trusted-url",
      "https://kyoto.travel/en/",
    ],
  )

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload["target"]["city"] == "Kyoto"
  assert payload["queries"] == [
    "Kyoto Japan official travel cafes",
    "Kyoto Japan cafes guide",
  ]
  assert payload["sources"] == [
    {
      "title": "https://kyoto.travel/en/",
      "url": "https://kyoto.travel/en/",
      "snippet": "Operator supplied trusted URL.",
      "query": None,
      "source_kind": "trusted_url",
      "trust_hint": "high",
    },
    {
      "title": "Kyoto Cafes",
      "url": "https://example.com/cafes",
      "snippet": "Cafe guide.",
      "query": "Kyoto Japan official travel cafes",
      "source_kind": "search_result",
      "trust_hint": "low",
    },
  ]


def test_research_city_runs_pipeline_and_prints_summary(monkeypatch) -> None:
  captured = {}

  class FakeSettings:
    default_model = "test-model"

  class FakeTrustedUrlFetcher:
    pass

  class FakeOllamaResearchAgent:
    def __init__(self, *, client, model: str) -> None:
      self.client = client
      self.model = model

  class FakeOllamaResearchCritic:
    def __init__(self, *, client, model: str) -> None:
      self.client = client
      self.model = model

  def fake_run_research_pipeline(**kwargs):
    captured.update(kwargs)
    return SimpleNamespace(
      run=FakeResearchRun(
        run_id="run-1",
        target=kwargs["target"].model_dump(mode="json"),
        model_name=kwargs["model_name"],
        status="completed",
        report={
          "stable_notes": 1,
          "candidates": 2,
          "blocked_items": 1,
          "publish_notes": False,
        },
        created_at="2026-05-09T10:00:00+00:00",
        updated_at="2026-05-09T10:01:00+00:00",
      ),
      validation=ResearchValidationReport(passed=True),
    )

  monkeypatch.setattr(cli_module, "get_settings", lambda: FakeSettings())
  monkeypatch.setattr(cli_module, "get_ollama_client", lambda: object())
  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "TrustedUrlFetcher", FakeTrustedUrlFetcher, raising=False)
  monkeypatch.setattr(cli_module, "OllamaResearchAgent", FakeOllamaResearchAgent, raising=False)
  monkeypatch.setattr(cli_module, "OllamaResearchCritic", FakeOllamaResearchCritic, raising=False)
  monkeypatch.setattr(cli_module, "run_research_pipeline", fake_run_research_pipeline, raising=False)

  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--trusted-url",
      "https://kyoto.travel/en/",
    ],
  )

  assert result.exit_code == 0
  assert captured["model_name"] == "test-model"
  assert captured["target"].city == "Kyoto"
  assert captured["target"].themes[0].value == "cafes"
  assert isinstance(captured["fetcher"], FakeTrustedUrlFetcher)
  assert isinstance(captured["research_agent"], FakeOllamaResearchAgent)
  assert isinstance(captured["critic"], FakeOllamaResearchCritic)

  payload = json.loads(result.output)
  assert payload == {
    "run_id": "run-1",
    "status": "completed",
    "target": {
      "country": "Japan",
      "city": "Kyoto",
      "themes": ["cafes"],
      "trusted_urls": ["https://kyoto.travel/en/"],
    },
    "model_name": "test-model",
    "report": {
      "stable_notes": 1,
      "candidates": 2,
      "blocked_items": 1,
      "publish_notes": False,
    },
    "validation": {
      "passed": True,
      "issues": [],
    },
  }


def test_research_city_uses_discovery_fetcher_when_web_search_enabled(monkeypatch) -> None:
  captured = {}

  class FakeSettings:
    default_model = "test-model"
    search_provider = "brave"
    brave_search_api_key = "secret"
    brave_search_country = "us"
    brave_search_lang = "en"

  class FakeDiscoveryUrlFetcher:
    def __init__(self, *, search_client) -> None:
      self.search_client = search_client

  class FakeOllamaResearchAgent:
    def __init__(self, *, client, model: str) -> None:
      self.client = client
      self.model = model

  def fake_build_source_search_client(settings):
    assert settings.search_provider == "brave"
    return "search-client"

  def fake_run_research_pipeline(**kwargs):
    captured.update(kwargs)
    return SimpleNamespace(
      run=FakeResearchRun(
        run_id="run-1",
        target=kwargs["target"].model_dump(mode="json"),
        model_name=kwargs["model_name"],
        status="completed",
        report={},
        created_at="2026-05-09T10:00:00+00:00",
        updated_at="2026-05-09T10:01:00+00:00",
      ),
      validation=ResearchValidationReport(passed=True),
    )

  monkeypatch.setattr(cli_module, "get_settings", lambda: FakeSettings())
  monkeypatch.setattr(cli_module, "get_ollama_client", lambda: object())
  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "build_source_search_client", fake_build_source_search_client)
  monkeypatch.setattr(cli_module, "DiscoveryUrlFetcher", FakeDiscoveryUrlFetcher, raising=False)
  monkeypatch.setattr(cli_module, "OllamaResearchAgent", FakeOllamaResearchAgent, raising=False)
  monkeypatch.setattr(cli_module, "run_research_pipeline", fake_run_research_pipeline, raising=False)

  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--web-search",
    ],
  )

  assert result.exit_code == 0
  assert isinstance(captured["fetcher"], FakeDiscoveryUrlFetcher)
  assert captured["fetcher"].search_client == "search-client"


def test_research_city_web_search_requires_configured_provider(monkeypatch) -> None:
  class FakeSettings:
    default_model = "test-model"
    search_provider = "none"
    brave_search_api_key = None
    brave_search_country = "us"
    brave_search_lang = "en"

  monkeypatch.setattr(cli_module, "get_settings", lambda: FakeSettings())
  monkeypatch.setattr(cli_module, "get_ollama_client", lambda: object())

  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--web-search",
    ],
  )

  assert result.exit_code == 1
  assert "Set SEARCH_PROVIDER=tavily or brave" in result.stderr


def test_list_research_runs_prints_saved_runs(monkeypatch) -> None:
  def fake_list_research_runs(session):
    return [
      FakeResearchRun(
        run_id="run-1",
        target={"country": "Japan", "city": "Kyoto", "themes": ["cafes"]},
        model_name="test-model",
        status="completed",
        report={"candidates": 3},
        created_at="2026-05-09T10:00:00+00:00",
        updated_at="2026-05-09T10:01:00+00:00",
      )
    ]

  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "list_research_runs", fake_list_research_runs)

  result = runner.invoke(cli_module.app, ["list-research-runs"])

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload == [
    {
      "run_id": "run-1",
      "target": {"country": "Japan", "city": "Kyoto", "themes": ["cafes"]},
      "model_name": "test-model",
      "status": "completed",
      "report": {"candidates": 3},
      "created_at": "2026-05-09T10:00:00+00:00",
      "updated_at": "2026-05-09T10:01:00+00:00",
    }
  ]


def test_show_research_run_prints_saved_run(monkeypatch) -> None:
  def fake_get_research_run(session, *, run_id: str):
    assert run_id == "run-1"
    return FakeResearchRun(
      run_id="run-1",
      target={"country": "Japan", "city": "Kyoto", "themes": ["cafes"]},
      model_name="test-model",
      status="completed",
      report={
        "stable_notes": 0,
        "candidates": 0,
        "blocked_items": 1,
        "blocked_item_details": [
          {
            "title": "Unsourced cafe list",
            "reason": "No source URL supported the listed cafes.",
            "source_urls": ["https://example.com/blocked-list"],
          }
        ],
      },
      created_at="2026-05-09T10:00:00+00:00",
      updated_at="2026-05-09T10:01:00+00:00",
    )

  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "get_research_run", fake_get_research_run)

  result = runner.invoke(cli_module.app, ["show-research-run", "run-1"])

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload["run_id"] == "run-1"
  assert payload["status"] == "completed"
  assert payload["report"]["blocked_item_details"][0]["title"] == "Unsourced cafe list"


def test_show_research_run_exits_for_missing_run(monkeypatch) -> None:
  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "get_research_run", lambda session, *, run_id: None)

  result = runner.invoke(cli_module.app, ["show-research-run", "missing"])

  assert result.exit_code == 1
  assert "Research run not found." in result.stderr


def test_search_candidates_prints_matching_options(monkeypatch) -> None:
  captured = {}

  def fake_search_candidate_options(**kwargs):
    captured.update(kwargs)
    return [
      SimpleNamespace(
        candidate_id="candidate-1",
        run_id="run-1",
        name="Quiet Coffee",
        category="cafe",
        country="Japan",
        city="Kyoto",
        area="Kawaramachi",
        description="Central cafe option.",
        price_level="moderate",
        trust_rating="medium",
        source_urls=["https://example.com"],
        last_checked_at="2026-05-09T10:00:00+00:00",
        metadata={},
      )
    ]

  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "search_candidate_options", fake_search_candidate_options)

  result = runner.invoke(
    cli_module.app,
    [
      "search-candidates",
      "--country",
      "Japan",
      "--city",
      "Kyoto",
      "--category",
      "cafe",
      "--min-trust",
      "medium",
      "--limit",
      "3",
    ],
  )

  assert result.exit_code == 0
  assert captured["country"] == "Japan"
  assert captured["city"] == "Kyoto"
  assert captured["category"] == "cafe"
  assert captured["min_trust"].value == "medium"
  assert captured["limit"] == 3
  payload = json.loads(result.output)
  assert payload["candidates"][0]["name"] == "Quiet Coffee"
  assert payload["candidates"][0]["source_urls"] == ["https://example.com"]


def test_search_candidates_rejects_invalid_min_trust() -> None:
  result = runner.invoke(
    cli_module.app,
    [
      "search-candidates",
      "--country",
      "Japan",
      "--city",
      "Kyoto",
      "--min-trust",
      "maybe",
    ],
  )

  assert result.exit_code == 1
  assert "Invalid trust rating: maybe" in result.stderr
