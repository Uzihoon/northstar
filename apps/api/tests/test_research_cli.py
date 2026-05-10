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
